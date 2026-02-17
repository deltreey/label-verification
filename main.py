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

app = FastAPI(title="Alcohol Label Warning Checker")


def upscale_for_detection(bgr):
    h, w = bgr.shape[:2]
    scale = 2.0
    return cv2.resize(bgr, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)


GOVT_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages "
    "during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)


def is_bold_and_all_caps(text: str, box: list) -> bool:
    """Simple proxy for bold/all-caps: check text.isupper() + box height variance (taller for bold)."""
    if not text.strip().upper().startswith("GOVERNMENT WARNING:"):
        return False
    # Box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] from PaddleOCR
    heights = [box[1][1] - box[0][1], box[2][1] - box[3][1]]  # vertical spans
    avg_height = sum(heights) / len(heights)
    # Heuristic: bold text often has larger vertical span or thicker contours (simplified)
    return text.isupper() and avg_height > 20  # Tune threshold on your images


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
