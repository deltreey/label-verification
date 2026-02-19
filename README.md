# Label Verification

Prototype API for assisting TTB alcohol label review.

The current design is intentionally conservative:
- default to human review
- reject when clear issues are found
- only rarely auto-pass

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python environment + dependency management)
- `make`
- Python `3.11+`
- Optional: [Docker](https://docs.docker.com/engine/) for containerized runs

## Quick Start

```bash
uv sync
make dev
```

This starts FastAPI on `http://0.0.0.0:8001`.
You can view the Swagger UI at `http://0.0.0.0:8001/docs`.

## Development Commands

- Start API: `make dev`
- Run tests: `make test`
- Build Docker image: `make build`

## API Endpoints

### `POST /review`

Multipart form-data:
- `image_file`: label image
- `pdf_file`: filled TTB form PDF

Runs OCR + PDF field extraction + rules evaluation.

Example:

```bash
curl -X POST http://localhost:8001/review \
  -F "image_file=@tests/fixtures/busch.jpg" \
  -F "pdf_file=@tests/fixtures/busch_application.pdf"
```

### `POST /review_with_fields`

Multipart form-data:
- `image_file`: label image
- `fields_json`: JSON object of field values keyed by YAML field names

Example:

```bash
curl -X POST http://localhost:8001/review_with_fields \
  -F "image_file=@tests/fixtures/busch.jpg" \
  -F 'fields_json={"Brand":"BUSCH","Product Type":"Malt"}'
```

### `POST /bulk`

Multipart form-data:
- `zip_file`: zip archive containing nested zip files

Each nested zip must contain:
- exactly 1 PDF
- exactly 1 non-PDF image (`.png/.jpg/.jpeg/.bmp/.tif/.tiff/.webp`)

Response is a JSON array with one review result per nested zip package.

Example:

```bash
curl -X POST http://localhost:8001/bulk \
  -F "zip_file=@/path/to/batch.zip"
```

## Assumptions

1. One image per label.  I know this is probably unrealistic, but for PoC it seems like a decent start.
2. For bulk upload, we're only supporting zip files with 2 files, one form and one image.  We can easily alter this to support the JSON fields, multiple images, or a manifest file later.  A real bulk upload would probably use a shared folder.
3. We're supporting only the exact PDF form from the website, filled in digitally.  We can parse the form in future phases.
4. We assume the optimal use case is to reject applications to save the humans' time parsing obviously invalid applications.
5. We're assuming the form is filled out correctly, and for the moment, we're assuming only actual applications even though the form supports renewals and whatnot.
6. We're assuming access to some sort of Azure AI capable box, like a GPU.  On my CPU-only workstation, this runs at ~10 seconds.  Faster AI processing is a requirement, not an option.
6. We're assuming there is more work to do and a lot of features not implemented, like font weight, font size, and lots of other rules.

## Project Structure

- `main.py`: FastAPI app and endpoints
- `logic/ocr.py`: OCR pipeline
- `logic/form510031_reader.py`: PDF form field extraction/mapping
- `logic/required_text.py`: YAML-backed requirement lists
- `logic/required_text.yaml`: requirements source data
- `logic/label_rules.py`: rule evaluation
- `tests/`: tests + fixtures

## Tools and Licenses

- Python: PSF License (`python.org`)
- FastAPI: MIT
- pypdf: BSD-3-Clause
- OpenCV (`opencv-python`): Apache-2.0
- Pillow: MIT-CMU
- PyYAML: MIT
- python-doctr: Apache-2.0
- Docker: Docker Engine licensing varies by usage and subscription tier

Use of this project must comply with all third-party package licenses in `pyproject.toml`.
For distribution or production use, verify exact dependency license terms and versions.

## Troubleshooting

- `make: uv: command not found`: install `uv` and ensure it is on `PATH`.
- Slow OCR: run on GPU-enabled hardware.
- `400` errors on `/bulk`: verify outer archive is a zip of zip files and each nested zip has exactly 1 PDF + 1 image.
