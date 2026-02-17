import os
import re
import tempfile
from dataclasses import dataclass
from typing import Any, List

import cv2
import numpy
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from rapidfuzz import fuzz


@dataclass
class OCR(object):
    file_contents: bytes
    model = ocr_predictor(
        det_arch="db_resnet50",
        reco_arch="vitstr_small",
        pretrained=True
    )
    processed_image = None
    text = None

    def __post_init__(self):
        self.processed_img = self.doctr_ocr_from_bytes()

    def decode_bytes_to_bgr(self, image_bytes: bytes) -> numpy.ndarray:
        arr = numpy.frombuffer(image_bytes, numpy.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("cv2.imdecode failed: not an image or corrupted bytes")
        return bgr

    def preprocess_for_doctr(self, bgr: numpy.ndarray) -> numpy.ndarray:
        """
        Return: RGB uint8 image (HxWx3) suitable for docTR.
        Avoid hard thresholding here; it hurts the detector.
        """
        # Contrast boost in LAB (safe for colored labels)
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, bb = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l2 = clahe.apply(l)

        lab2 = cv2.merge([l2, a, bb])
        bgr2 = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

        # Mild denoise (don’t overdo or you smear small fonts)
        bgr2 = cv2.fastNlMeansDenoisingColored(bgr2, None, 5, 5, 7, 21)

        # Optional: gentle sharpen
        kernel = numpy.array([[0, -1, 0],
                           [-1,  5, -1],
                           [0, -1, 0]], dtype=numpy.float32)
        bgr2 = cv2.filter2D(bgr2, -1, kernel)

        rgb = cv2.cvtColor(bgr2, cv2.COLOR_BGR2RGB)
        return rgb

    def doctr_ocr_from_bytes(self) -> dict:
        image_bytes = self.file_contents
        bgr = self.decode_bytes_to_bgr(image_bytes)
        rgb = self.preprocess_for_doctr(bgr)

        # docTR expects a file path in your version
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name

        # cv2 writes BGR, so convert back for writing
        bgr_out = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(tmp_path, bgr_out)
        if not ok:
            raise RuntimeError("cv2.imwrite failed")

        try:
            doc = DocumentFile.from_images([tmp_path])
            result = self.model(doc)
            # page = result.pages[0]
            # img = page.render()
            # img.save("debug_boxes.png")
            return result.export()
        finally:
            os.remove(tmp_path)

    def doctr_export_to_text(
            self,
            export: dict[str, Any],
            *,
            min_word_conf: float = 0.0,
            drop_single_char_below: float = 0.0,
    ) -> str:
        """
        Convert docTR result.export() dict -> plain text.

        Args:
          min_word_conf: drop any word with confidence below this.
          drop_single_char_below: if a word is 1 char long and confidence is below this, drop it
                                  (useful for stray '-' '>' etc).
        """
        lines_out: list[tuple[float, float, str]] = []  # (y, x, text)

        for page in export.get("pages", []):
            for block in page.get("blocks", []):
                for line in block.get("lines", []):
                    # line geometry: ((x0, y0), (x1, y1)) normalized 0..1
                    (x0, y0), (x1, y1) = line.get("geometry", ((0.0, 0.0), (0.0, 0.0)))

                    words = []
                    for w in line.get("words", []):
                        val = (w.get("value") or "").strip()
                        if not val:
                            continue
                        conf = float(w.get("confidence", 0.0))

                        if conf < min_word_conf:
                            continue
                        if len(val) == 1 and conf < drop_single_char_below:
                            continue

                        words.append(val)

                    if not words:
                        continue

                    text = " ".join(words)
                    lines_out.append((float(y0), float(x0), text))

        # reading order: top-to-bottom, then left-to-right
        lines_out.sort(key=lambda t: (t[0], t[1]))
        return "\n".join(t[2] for t in lines_out)

    def fuzzy_contains(self, haystack, needle):
        score = fuzz.partial_ratio(needle, haystack)
        return score

    def subsequence_contains(self, haystack: str, needle: str, case_sensitive=False) -> bool:
        """
        True if all needle_tokens appear in order in haystack_tokens (not necessarily contiguous).
        This would not work on gigantic text arrays, but most label text is relatively short
        """
        file_contents = re.sub(r'\s+', '', haystack)
        search_text = re.sub(r'\s+', '', needle)
        j = 0
        for h in range(len(file_contents)):
            hay = file_contents[h]
            if j >= len(search_text):
                break
            if not case_sensitive and hay.lower() == search_text[j].lower():
                j += 1
            elif hay == search_text[j]:
                j += 1
        return j == len(search_text)

    def has_text(self, text_to_find, exact=False):
        processed_img = self.doctr_ocr_from_bytes()
        self.text = self.doctr_export_to_text(processed_img, min_word_conf=0.4, drop_single_char_below=0.8)
        # print(text)

        idx = self.text.find(text_to_find[0]) # first character
        if idx < 0:
            return {"ok": False, "reason": "missing_or_not_all_caps_header"}

        if exact:
            ok = self.subsequence_contains(self.text, text_to_find, case_sensitive=True)
            return {"ok": ok, "reason": None if ok else "missing_required_tokens"}
        else:
            score = self.fuzzy_contains(self.text, text_to_find)
            ok = score > 100
            return {"ok": ok, "reason": None if ok else f"Score too low: {score}"}


