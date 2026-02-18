import os
import tempfile
import unicodedata
from typing import Any, List

import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from PIL import Image
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import re

from logic.ocr import OCR
from logic.required_text import RequiredText

app = FastAPI(title="Alcohol Label Warning Checker")


@app.post("/review")
async def review(image_file: UploadFile = File(...), pdf_file: UploadFile = File(...)):
    response = {}
    try:
        contents = await image_file.read()
        ocr = OCR(file_contents=contents)
        if ocr.processed_img is None:
            response = {
                "decision": "Human Review",
                "confidence": 0.0,
                "full_text": "",
                "findings": ocr.findings
            }
        basic_check = ocr.has_text('GOVERNMENT WARNING')
        if not basic_check['ok']:
            ocr.findings.append('GOVERNMENT WARNING header not found')
            response = {
                "decision": "Reject",
                "confidence": basic_check['confidence'],
                "full_text": ocr.text,
                "findings": ocr.findings
            }
        else:
            ocr.findings.append('GOVERNMENT WARNING header found')
            requirements = RequiredText(type="all").as_list() # @TODO: swap this for specific types by form inputs
            for item in requirements:
                found = ocr.has_text(item)
                if found:
                    ocr.findings.append(f"Required text '{item}' found")
                else:
                    ocr.findings.append(f"Required text '{item}' not found")
                    response = {
                        "decision": "Reject",
                        "confidence": found['confidence'],
                        "full_text": ocr.text,
                        "findings": ocr.findings
                    }
                    break
            response = {
                "decision": "Human Review",
                "confidence": 0.0,
                "full_text": ocr.text,
                "findings": ocr.findings
            }
    except Exception as err:
        response = {
            "decision": "Human Review",
            "confidence": 0.0,
            "full_text": "",
            "findings": ["Error Occurred", f"Exception: {err}"]
        }
    finally:
        return JSONResponse(response)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info", reload=False)
