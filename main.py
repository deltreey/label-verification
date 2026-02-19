import os
import tempfile
import unicodedata
from typing import Any, List
import json
from io import BytesIO
import zipfile

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from PIL import Image
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import re

from logic import label_rules
from logic.form510031_reader import TTBForm510031Reader
from logic.ocr import OCR
from logic.required_text import RequiredText

app = FastAPI(title="Alcohol Label Warning Checker")


@app.post("/review")
async def review(image_file: UploadFile = File(...), pdf_file: UploadFile = File(...)):
    response = {}
    try:
        # if we crash at OCR, let's do it early
        contents = await image_file.read()
        ocr = OCR(file_contents=contents)
        if ocr.processed_img is None:
            response = {
                "decision": "Human Review",
                "confidence": 0.0,
                "full_text": "",
                "findings": ocr.findings
            }
            return response
        form_bytes = await pdf_file.read()
        form = TTBForm510031Reader(form_bytes)
        fields = form.get_values_by_field_mapping()
        response = label_rules.check_rules(ocr, fields)
    except Exception as err:
        response = {
            "decision": "Human Review",
            "confidence": 0.0,
            "full_text": "",
            "findings": ["Error Occurred", f"Exception: {err}"]
        }
    finally:
        return JSONResponse(response)


@app.post("/review_with_fields")
async def review_with_fields(image_file: UploadFile = File(...), fields_json: str = Form(...)):
    response = {}
    try:
        try:
            fields = json.loads(fields_json)
        except json.JSONDecodeError:
            return JSONResponse(
                {
                    "decision": "Human Review",
                    "confidence": 0.0,
                    "full_text": "",
                    "findings": ["Invalid fields_json. Expected a JSON array of YAML field names."],
                },
                status_code=400,
            )

        if not isinstance(fields, dict):
            return JSONResponse(
                {
                    "decision": "Human Review",
                    "confidence": 0.0,
                    "full_text": "",
                    "findings": ["Invalid fields_json. Expected a JSON dictionary."],
                },
                status_code=400,
            )
        contents = await image_file.read()
        ocr = OCR(file_contents=contents)
        if ocr.processed_img is None:
            return JSONResponse(
                {
                    "decision": "Human Review",
                    "confidence": 0.0,
                    "full_text": "",
                    "findings": ocr.findings,
                }
            )

        response = label_rules.check_rules(ocr, fields)
    except Exception as err:
        response = {
            "decision": "Human Review",
            "confidence": 0.0,
            "full_text": "",
            "findings": ["Error Occurred", f"Exception: {err}"],
        }
    finally:
        return JSONResponse(response)


@app.post("/bulk")
async def bulk(zip_file: UploadFile = File(...)):
    try:
        outer_bytes = await zip_file.read()
        outer_buffer = BytesIO(outer_bytes)
        if not zipfile.is_zipfile(outer_buffer):
            return JSONResponse(
                {
                    "findings": ["Uploaded file must be a zip archive containing nested zip files."]
                },
                status_code=400,
            )

        results: list[dict[str, Any]] = []
        with zipfile.ZipFile(BytesIO(outer_bytes)) as outer_zip:
            for nested_info in outer_zip.infolist():
                if nested_info.is_dir():
                    continue

                nested_name = nested_info.filename
                if not nested_name.lower().endswith(".zip"):
                    results.append(
                        {
                            "package": nested_name,
                            "decision": "Human Review",
                            "confidence": 0.0,
                            "full_text": "",
                            "findings": ["Skipped: top-level entry is not a zip file."],
                        }
                    )
                    continue

                nested_bytes = outer_zip.read(nested_info)
                nested_buffer = BytesIO(nested_bytes)
                if not zipfile.is_zipfile(nested_buffer):
                    results.append(
                        {
                            "package": nested_name,
                            "decision": "Human Review",
                            "confidence": 0.0,
                            "full_text": "",
                            "findings": ["Invalid nested zip file."],
                        }
                    )
                    continue

                try:
                    with zipfile.ZipFile(BytesIO(nested_bytes)) as nested_zip:
                        files = [f for f in nested_zip.infolist() if not f.is_dir()]

                        pdf_entries = [f for f in files if f.filename.lower().endswith(".pdf")]
                        image_entries = [
                            f for f in files if f.filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"))
                        ]

                        if len(pdf_entries) != 1 or len(image_entries) != 1:
                            results.append(
                                {
                                    "package": nested_name,
                                    "decision": "Human Review",
                                    "confidence": 0.0,
                                    "full_text": "",
                                    "findings": [
                                        "Each nested zip must contain exactly 1 PDF and exactly 1 image (non-PDF).",
                                        f"Found pdf={len(pdf_entries)} image={len(image_entries)}",
                                    ],
                                }
                            )
                            continue

                        pdf_bytes = nested_zip.read(pdf_entries[0])
                        image_bytes = nested_zip.read(image_entries[0])

                        ocr = OCR(file_contents=image_bytes)
                        if ocr.processed_img is None:
                            results.append(
                                {
                                    "package": nested_name,
                                    "decision": "Human Review",
                                    "confidence": 0.0,
                                    "full_text": "",
                                    "findings": ocr.findings,
                                }
                            )
                            continue

                        form = TTBForm510031Reader(pdf_bytes)
                        fields = form.get_values_by_field_mapping()
                        response = label_rules.check_rules(ocr, fields)
                        response["package"] = nested_name
                        results.append(response)
                except Exception as err:
                    results.append(
                        {
                            "package": nested_name,
                            "decision": "Human Review",
                            "confidence": 0.0,
                            "full_text": "",
                            "findings": ["Error Occurred", f"Exception: {err}"],
                        }
                    )

        return JSONResponse(results)
    except Exception as err:
        return JSONResponse(
            [
                {
                    "package": getattr(zip_file, "filename", "unknown"),
                    "decision": "Human Review",
                    "confidence": 0.0,
                    "full_text": "",
                    "findings": ["Error Occurred", f"Exception: {err}"],
                }
            ]
        )


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info", reload=False)
