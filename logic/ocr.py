import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, ClassVar

import cv2
import numpy
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from rapidfuzz import fuzz


@dataclass
class OCR(object):
    file_contents: bytes
    model: ClassVar[Any] = ocr_predictor(
        det_arch="db_resnet50",
        reco_arch="vitstr_small",
        pretrained=True
    )
    processed_img: dict[str, Any] | None = field(init=False, default=None)
    text: str | None = field(init=False, default=None)
    findings: list[str] = field(init=False, default_factory=list)

    def __post_init__(self):
        self.processed_img = self.doctr_ocr_from_bytes()

    def upscale_for_detection(self, bgr):
        h, w = bgr.shape[:2]
        scale = 2.0
        return cv2.resize(bgr, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)

    def is_bold_and_all_caps(self, text: str, box: list) -> bool:
        """Simple proxy for bold/all-caps: check text.isupper() + box height variance (taller for bold)."""
        if not text.strip().upper().startswith("GOVERNMENT WARNING:"):
            return False
        # Box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] from PaddleOCR
        heights = [box[1][1] - box[0][1], box[2][1] - box[3][1]]  # vertical spans
        avg_height = sum(heights) / len(heights)
        # Heuristic: bold text often has larger vertical span or thicker contours (simplified)
        return text.isupper() and avg_height > 20  # Tune threshold on your images

    def decode_bytes_to_bgr(self, image_bytes: bytes) -> numpy.ndarray:
        arr = numpy.frombuffer(image_bytes, numpy.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("cv2.imdecode failed: not an image or corrupted bytes")
        return bgr

    def preprocess_for_doctr(self, bgr: numpy.ndarray) -> numpy.ndarray:
        """
        Return: BGR uint8 image (HxWx3) suitable for docTR.
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

        # rgb = cv2.cvtColor(bgr2, cv2.COLOR_BGR2RGB)
        return bgr2

    def doctr_ocr_from_bytes(self) -> dict:
        doc = DocumentFile.from_images(self.file_contents)
        result = self.model(doc)
        metrics = self.ocr_quality_metrics(result)
        if metrics['ok']:
            self.findings.append("OCR processing successful")
            self.findings.append("OCR no preprocessing required")
            return result.export()
        else:
            bgr = self.decode_bytes_to_bgr(self.file_contents)
            bgr = self.preprocess_for_doctr(bgr)
            success, encoded = cv2.imencode(".png", bgr)
            if not success:
                raise ValueError("Image encoding failed")
            doc = DocumentFile.from_images([encoded])
            result = self.model(doc)
            metrics = self.ocr_quality_metrics(result)
            if metrics['ok']:
                self.findings.append("OCR processing successful")
                self.findings.append("OCR preprocessing required")
                return result.export()
        self.findings.append("OCR processing failed")
        return None

    def iter_words(self, doctr_doc):
        # doctr_doc.pages -> blocks -> lines -> words
        for page in doctr_doc.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        yield word

    def looks_garbage(self, token: str) -> bool:
        VOWEL_RE = re.compile(r"[aeiouAEIOU]")
        ALNUM_RE = re.compile(r"[A-Za-z0-9]")
        t = token.strip()
        if not t:
            return True
        if len(t) == 1 and not t.isalnum(): # lone punctuation like "-" "&"
            return True
        if not ALNUM_RE.search(t): # no letters/digits
            return True
        if len(t) >= 6 and not VOWEL_RE.search(t):  # "FTSXZP" or other junk that's not a word
            return True
        return False

    def ocr_quality_metrics(self, doctr_result):
        words = list(self.iter_words(doctr_result))
        if not words:
            return {"ok": False, "reason": "no_words", "word_count": 0}

        confs = []
        weights = []
        garbage = 0
        low_conf = 0

        for w in words:
            txt = w.value or ""
            conf = float(getattr(w, "confidence", 0.0))
            length = max(len(txt.strip()), 1)

            confs.append(conf)
            weights.append(length)

            if conf < 0.6:
                low_conf += 1
            if self.looks_garbage(txt):
                garbage += 1

        weight = sum(weights)
        mean_conf = sum(c * wt for c, wt in zip(confs, weights)) / weight
        low_conf_frac = low_conf / len(words)
        garbage_frac = garbage / len(words)

        # Very simple gate rules (tune later)
        ok = True
        reasons = []

        if len(words) < 30:
            ok = False; reasons.append("too_few_words")
        if garbage_frac > 0.35:
            ok = False; reasons.append("too_much_garbage")
        if mean_conf < 0.75 and garbage_frac > 0.20:
            ok = False; reasons.append("low_conf_and_garbage")

        return {
            "ok": ok,
            "reasons": reasons,
            "word_count": len(words),
            "mean_conf": round(mean_conf, 3),
            "low_conf_frac": round(low_conf_frac, 3),
            "garbage_frac": round(garbage_frac, 3),
        }

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
        self.text = self.doctr_export_to_text(self.processed_img)

        if exact:
            ok = self.subsequence_contains(self.text, text_to_find, case_sensitive=True)
            return {
                "ok": ok,
                "reason": None if ok else "missing_required_tokens"
            }
        else:
            score = self.fuzzy_contains(self.text, text_to_find)
            ok = score > 70
            return {
                "ok": ok,
                "confidence": score
            }

