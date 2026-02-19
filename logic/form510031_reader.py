from __future__ import annotations

from io import BytesIO
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from pypdf import PdfReader


@dataclass
class TTBForm510031Reader:
    """Read TTB F 5100.31 and expose values by PDF and YAML field names."""

    pdf_file: bytes | str | Path

    field_mapping: list[str] = field(default_factory=list)
    pdf_fields: dict[str, dict[str, Any]] = field(init=False, default_factory=dict)
    field_values: dict[str, str | None] = field(init=False, default_factory=dict)

    DEFAULT_YAML_FIELD_MAPPING: ClassVar[tuple[str, ...]] = (
        "Brand",
        "Designation",
        "Name and Address",
        "Country of Origin",
        "Net Contents",
        "Alcohol Content",
        "Sulfite and Aspartame Declarations",
        "Class or Type Designation",
        "Color Additive Disclosure",
        "Product Type",
        "Product Source",
        "Application Type",
    )

    PDF_TO_YAML_FIELD_MAPPING: ClassVar[dict[str, tuple[str, ...]]] = {
        "6. BRAND NAME (Required)": ("Brand",),
        "7. FANCIFUL NAME (If any)": ("Designation",),
        "10. GRAPE VARIETAL(S) Wine only": ("Designation",),
        "11. WINE APPELLATION (If on label)": ("Designation",),
        "8. NAME AND ADDRESS OF APPLICANT AS SHOWN ON PLANT REGISTRY, BASIC": ("Name and Address",),
        "8a. MAILING ADDRESS, IF DIFFERENT": ("Name and Address",),
        "Check Box22": ("Class or Type Designation", "Product Type"),
        "Check Box34": ("Product Source",),
        "14a. CERTIFICATE OF LABEL APPROVAL": ("Application Type",),
        "14b. CERTIFICATE OF EXEMPTION FROM LABEL APPROVAL": ("Application Type",),
        "14c. DISTINCTIVE LIQUOR BOTTLE APPROVAL": ("Application Type",),
        "14d. RESUBMISSION AFTER REJECTION": ("Application Type",),
        "15.  SHOW ANY INFORMATION THAT IS BLOWN, BRANDED, OR EMBOSSED ON THE CONTAINER (e.g., net contents) ONLY IF IT DOES NOT APPEAR ON THE LABELS": (
            "Country of Origin",
            "Net Contents",
            "Alcohol Content",
            "Sulfite and Aspartame Declarations",
            "Color Additive Disclosure",
        ),
    }

    def __post_init__(self) -> None:
        self.pdf_fields = self._load_pdf_fields()
        self.field_values = {
            pdf_name: self._extract_field_value(field_obj)
            for pdf_name, field_obj in self.pdf_fields.items()
        }
        if not self.field_mapping:
            self.field_mapping = list(self.DEFAULT_YAML_FIELD_MAPPING)

    def _load_pdf_fields(self) -> dict[str, dict[str, Any]]:
        if isinstance(self.pdf_file, bytes):
            reader = PdfReader(BytesIO(self.pdf_file))
        else:
            reader = PdfReader(str(self.pdf_file))
        if reader.is_encrypted:
            reader.decrypt("")
        return reader.get_fields() or {}

    def available_pdf_field_names(self) -> list[str]:
        return sorted(self.pdf_fields.keys())

    @staticmethod
    def _clean_pdf_value(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if text.startswith("/"):
            text = text[1:]
        return text or None

    def _extract_field_value(self, field_obj: dict[str, Any]) -> str | None:
        if field_obj.get("/FT") == "/Btn":
            value = self._clean_pdf_value(field_obj.get("/V"))
            if value and value != "Off":
                return value
            for kid_ref in field_obj.get("/Kids", []) or []:
                kid = kid_ref.get_object()
                kid_value = self._clean_pdf_value(kid.get("/AS"))
                if kid_value and kid_value != "Off":
                    return kid_value
            return None

        value = self._clean_pdf_value(field_obj.get("/V"))
        return value

    @classmethod
    def _yaml_to_pdf_field_mapping(cls) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for pdf_field_name, yaml_names in cls.PDF_TO_YAML_FIELD_MAPPING.items():
            for yaml_name in yaml_names:
                out.setdefault(yaml_name, []).append(pdf_field_name)
        return out

    def get_value_by_pdf_field_name(self, pdf_field_name: str) -> str | None:
        return self.field_values.get(pdf_field_name)

    def get_value_by_field_mapping_name(self, mapping_name: str) -> str | None:
        yaml_to_pdf = self._yaml_to_pdf_field_mapping()
        pdf_names = yaml_to_pdf.get(mapping_name, [])
        if not pdf_names:
            return None

        values: list[str] = []
        for pdf_name in pdf_names:
            value = self.get_value_by_pdf_field_name(pdf_name)
            if value:
                values.append(value)

        if not values:
            return None
        values = list(dict.fromkeys(values))
        if len(values) == 1:
            return values[0]
        return "\n".join(values)

    def get_values_by_field_mapping(self) -> dict[str, str | None]:
        out: dict[str, str | None] = {}
        for mapping_name in self.field_mapping:
            out[mapping_name] = self.get_value_by_field_mapping_name(mapping_name)
        return out
