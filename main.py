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


def upscale_for_detection(bgr):
    h, w = bgr.shape[:2]
    scale = 2.0
    return cv2.resize(bgr, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)


def is_bold_and_all_caps(text: str, box: list) -> bool:
    """Simple proxy for bold/all-caps: check text.isupper() + box height variance (taller for bold)."""
    if not text.strip().upper().startswith("GOVERNMENT WARNING:"):
        return False
    # Box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] from PaddleOCR
    heights = [box[1][1] - box[0][1], box[2][1] - box[3][1]]  # vertical spans
    avg_height = sum(heights) / len(heights)
    # Heuristic: bold text often has larger vertical span or thicker contours (simplified)
    return text.isupper() and avg_height > 20  # Tune threshold on your images

@app.post("/review")
async def review(file: UploadFile = File(...)):
    response = {}
    try:
        contents = await file.read()
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



@app.post("/check-warning")
async def check_warning(file: UploadFile = File(...)):
    contents = await file.read()
    ocr = OCR(file_contents=contents)
    match = ocr.has_text(GOVT_WARNING, exact=True)
    print(match)
    bold_caps_found = False # use font width

    return JSONResponse({
        "found": match['ok'],
        "bold_caps_detected": bold_caps_found,
        "confidence": 0.0,  # placeholder
        # "extracted_snippets": extracted_texts[:5],  # top 5 for debug
        "full_extracted": ocr.text,
        "flags": ["No bold detected on header" if not bold_caps_found else None],
        "reason": match['reason']
    })

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info", reload=False)
