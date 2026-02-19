from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import app


FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(app)


def _read_fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_review_valid_busch_fixture_returns_reject() -> None:
    image_bytes = _read_fixture_bytes("busch.jpg")
    pdf_bytes = _read_fixture_bytes("busch_application.pdf")

    response = client.post(
        "/review",
        files={
            "image_file": ("busch.jpg", image_bytes, "image/jpeg"),
            "pdf_file": ("busch_application.pdf", pdf_bytes, "application/pdf"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "Reject"
    assert "findings" in body


def test_review_invalid_image_returns_human_review() -> None:
    pdf_bytes = _read_fixture_bytes("busch_application.pdf")

    response = client.post(
        "/review",
        files={
            "image_file": ("not_an_image.jpg", b"not-image-content", "image/jpeg"),
            "pdf_file": ("busch_application.pdf", pdf_bytes, "application/pdf"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "Human Review"
    assert "findings" in body


def test_review_invalid_pdf_returns_human_review() -> None:
    image_bytes = _read_fixture_bytes("busch.jpg")

    response = client.post(
        "/review",
        files={
            "image_file": ("busch.jpg", image_bytes, "image/jpeg"),
            "pdf_file": ("not_a_pdf.pdf", b"not-pdf-content", "application/pdf"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "Human Review"
    assert "Exception" in " ".join(body["findings"])


def test_review_with_fields_valid_payload_returns_reject() -> None:
    image_bytes = _read_fixture_bytes("busch.jpg")
    fields = {"Product Type": "malt", "Brand": "BUSCH"}

    response = client.post(
        "/review_with_fields",
        files={"image_file": ("busch.jpg", image_bytes, "image/jpeg")},
        data={"fields_json": json.dumps(fields)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "Reject"
    assert "findings" in body


def test_review_with_fields_invalid_json_returns_human_review() -> None:
    image_bytes = _read_fixture_bytes("busch.jpg")

    response = client.post(
        "/review_with_fields",
        files={"image_file": ("busch.jpg", image_bytes, "image/jpeg")},
        data={"fields_json": "{not-json"},
    )

    assert response.status_code == 400
    body = response.json()
    print(body)
    assert body["decision"] == "Human Review"


def test_review_with_fields_invalid_type_returns_human_review() -> None:
    image_bytes = _read_fixture_bytes("busch.jpg")

    response = client.post(
        "/review_with_fields",
        files={"image_file": ("busch.jpg", image_bytes, "image/jpeg")},
        data={"fields_json": json.dumps(["Product Type", "Brand"])},
    )

    assert response.status_code == 400
    body = response.json()
    print(body)
    assert body["decision"] == "Human Review"


def test_bulk_valid_nested_zip_returns_array_of_results() -> None:
    zip_bytes = _read_fixture_bytes("tests.zip")

    response = client.post(
        "/bulk",
        files={"zip_file": ("tests.zip", zip_bytes, "application/zip")},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 3
    assert all(item["decision"] == "Human Review" or item['decision'] == 'Reject' for item in body)


def test_bulk_invalid_non_zip_upload_returns_400() -> None:
    image_bytes = _read_fixture_bytes("busch.jpg")

    response = client.post(
        "/bulk",
        files={"zip_file": ("busch.jpg", image_bytes, "image/jpeg")},
    )

    assert response.status_code == 400
    body = response.json()
    assert "findings" in body


def test_bulk_invalid_non_nested_zip_returns_skipped_entries() -> None:
    zip_bytes = _read_fixture_bytes("busch_test.zip")

    response = client.post(
        "/bulk",
        files={"zip_file": ("busch_test.zip", zip_bytes, "application/zip")},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert all(item["decision"] == "Human Review" for item in body)
    assert all("Skipped" in " ".join(item["findings"]) for item in body)
