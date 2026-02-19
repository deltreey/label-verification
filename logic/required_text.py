from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RequiredText:
    type: str = "all"
    yaml_path: Path = field(default_factory=lambda: Path(__file__).with_name("required_text.yaml"))
    required: list[str] = field(init=False, default_factory=list)
    field_mapping: list[str] = field(init=False, default_factory=list)
    type_list: list[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        entries = self._load_yaml_entries()
        type_required = self._required_by_type(entries, self.type)
        all_required = self._required_by_type(entries, "all")
        self.required = type_required + all_required
        type_field_mapping = self._field_mapping_by_type(entries, self.type)
        all_field_mapping = self._field_mapping_by_type(entries, "all")
        self.field_mapping = type_field_mapping + all_field_mapping
        type_type_list = self._type_list_by_type(entries, self.type)
        self.type_list = type_type_list

    def as_required_list(self) -> list[str]:
        return self.required

    def as_field_mapping_list(self) -> list[str]:
        return self.field_mapping

    def as_type_list(self) -> list[str]:
        return self.type_list

    def _load_yaml_entries(self) -> list[dict[str, Any]]:
        with self.yaml_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or []
        if not isinstance(data, list):
            raise ValueError(f"{self.yaml_path} must be a YAML list of type entries")
        return data

    @staticmethod
    def _required_by_type(entries: list[dict[str, Any]], text_type: str) -> list[str]:
        required: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") != text_type:
                continue
            values = entry.get("required", []) or []
            if not isinstance(values, list):
                raise ValueError(f"required for type '{text_type}' must be a list")
            required.extend(str(value) for value in values)
        return required

    @staticmethod
    def _field_mapping_by_type(entries: list[dict[str, Any]], text_type: str) -> list[str]:
        mapped_fields: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") != text_type:
                continue
            values = entry.get("field_mapping", []) or []
            if not isinstance(values, list):
                raise ValueError(f"field_mapping for type '{text_type}' must be a list")
            mapped_fields.extend(str(value) for value in values)
        return mapped_fields

    @staticmethod
    def _type_list_by_type(entries: list[dict[str, Any]], text_type: str) -> list[str]:
        product_types: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") != text_type:
                continue
            values = entry.get("type_list", []) or []
            if not isinstance(values, list):
                raise ValueError(f"type_list for type '{text_type}' must be a list")
            product_types.extend(str(value) for value in values)
        return product_types
