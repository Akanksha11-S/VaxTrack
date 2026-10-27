"""OCR pipeline: PDF/image -> preprocessed image(s) -> Tesseract -> text lines with confidence.

Notes
- PDFs are rendered with PyMuPDF, so Windows users do not need to install Poppler.
- Digital PDFs that already contain selectable text are read directly (no OCR, no confidence).
- Text read from documents is never written to the application log.
"""
import io
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from config import settings

try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # pragma: no cover
    pytesseract = None

WINDOWS_DEFAULT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class OCRError(Exception):
    """An error whose message is safe to show to the user."""

    def __init__(self, message: str, code: str = "ocr_error"):
        super().__init__(message)
        self.message, self.code = message, code


@dataclass
class OCRLine:
    text: str
    confidence: float | None  # 0-100, None when the text came from a PDF text layer
    page: int = 1


@dataclass
class OCRResult:
    lines: list[OCRLine]
    page_count: int
    engine: str
    average_confidence: float | None


def configure_tesseract() -> str | None:
    """Locate the Tesseract executable. Returns its path, or None if it can't be found."""
    if pytesseract is None:
        return None
    candidates = [settings.TESSERACT_CMD, shutil.which("tesseract"), WINDOWS_DEFAULT]
    for path in candidates:
        if path and (os.path.isfile(path) or shutil.which(path)):
            pytesseract.pytesseract.tesseract_cmd = path
            return path
    return None


def is_available() -> bool:
    return configure_tesseract() is not None


# ------------------------------------------------------------------ preprocessing
def preprocess(image: Image.Image) -> list[tuple[str, np.ndarray]]:
    """Return image variants to try: contrast-enhanced grayscale and an adaptive threshold."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    if min(h, w) < 40:
        raise OCRError("The image is too small to read. Try a larger or clearer photo.", "image_too_small")

    long_side = max(h, w)
    if long_side < 1800:  # enlarge small photos so characters are tall enough for Tesseract
        factor = min(3.0, 2200 / long_side)
        gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    elif long_side > 3600:
        factor = 3000 / long_side
        gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)

    if float(gray.std()) < 3:
        raise OCRError("The image looks blank. Check that you uploaded the right file.", "blank_image")

    denoised = cv2.medianBlur(gray, 3)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(denoised)
    thresholded = cv2.adaptiveThreshold(
        cv2.GaussianBlur(clahe, (3, 3), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 15
    )
    return [("no_lines", remove_table_lines(clahe)), ("grayscale", clahe), ("threshold", thresholded)]


def remove_table_lines(gray: np.ndarray) -> np.ndarray:
    """Erase long horizontal/vertical rules. Vaccination cards are usually ruled tables, and Tesseract
    treats the boxes as graphics and skips the text inside them."""
    h, w = gray.shape
    _, inverted = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    horizontal = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(60, w // 15), 1)))
    vertical = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(60, h // 15))))
    rules = cv2.dilate(cv2.add(horizontal, vertical), np.ones((3, 3), np.uint8))
    cleaned = gray.copy()
    cleaned[rules > 0] = int(np.median(gray))
    return cleaned


# ------------------------------------------------------------------ Tesseract
def _run_tesseract(arr: np.ndarray, page: int, psm: int = 6) -> tuple[list[OCRLine], int]:
    try:
        data = pytesseract.image_to_data(
            arr, lang="eng", config=f"--oem 3 --psm {psm}", output_type=Output.DICT, timeout=90
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError(
            "Tesseract OCR is not installed or could not be found. See the README for setup steps.", "tesseract_missing"
        ) from exc
    except RuntimeError as exc:  # timeout
        raise OCRError("Reading the document took too long. Try a smaller or clearer image.", "ocr_timeout") from exc

    grouped: dict[tuple, list[tuple[str, float]]] = {}
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1
        if not text or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        grouped.setdefault(key, []).append((text, conf))

    lines, good_chars = [], 0
    for words in grouped.values():
        text = " ".join(w for w, _ in words)
        conf = sum(c for _, c in words) / len(words)
        lines.append(OCRLine(text=text, confidence=round(conf, 1), page=page))
        good_chars += sum(len(w) for w, c in words if c >= 60)
    return lines, good_chars


# (variant name, page segmentation mode). The best-scoring pass wins; extra passes only run when
# the earlier ones found little text.
PASSES = [("no_lines", 6), ("no_lines", 4), ("grayscale", 4)]
ENOUGH_CHARS = 120


def _ocr_image(image: Image.Image, page: int) -> list[OCRLine]:
    variants = dict(preprocess(image))
    best_lines, best_score = [], -1
    for name, psm in PASSES:
        lines, score = _run_tesseract(variants[name], page, psm)
        if score > best_score:
            best_lines, best_score = lines, score
        if best_score >= ENOUGH_CHARS and len(best_lines) >= 4:
            break
    return best_lines


# ------------------------------------------------------------------ entry point
def read_document(path: Path, file_type: str) -> OCRResult:
    if file_type == "pdf":
        return _read_pdf(path)
    if not is_available():
        raise OCRError(
            "Tesseract OCR is not installed or could not be found. See the README for setup steps.", "tesseract_missing"
        )
    try:
        with Image.open(path) as img:
            img.load()
            lines = _ocr_image(img, 1)
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError("This image couldn't be opened. Try a different file.", "unreadable_image") from exc
    return _result(lines, 1, "tesseract")


def _read_pdf(path: Path) -> OCRResult:
    import fitz  # PyMuPDF

    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise OCRError("This PDF couldn't be opened. It may be damaged or password protected.", "unreadable_pdf") from exc
    if doc.needs_pass:
        raise OCRError("This PDF is password protected. Remove the password and upload it again.", "pdf_locked")
    if doc.page_count == 0:
        raise OCRError("This PDF has no pages.", "empty_pdf")

    lines: list[OCRLine] = []
    used_ocr = False
    pages = min(doc.page_count, settings.MAX_PDF_PAGES)
    for index in range(pages):
        page = doc.load_page(index)
        text = page.get_text("text").strip()
        if len(text) >= 30:  # selectable text layer
            lines.extend(OCRLine(t.strip(), None, index + 1) for t in text.splitlines() if t.strip())
            continue
        if not is_available():
            raise OCRError(
                "This PDF is a scan and needs Tesseract OCR, which is not installed. See the README for setup steps.",
                "tesseract_missing",
            )
        pix = page.get_pixmap(dpi=300)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        lines.extend(_ocr_image(image, index + 1))
        used_ocr = True
    return _result(lines, doc.page_count, "tesseract" if used_ocr else "pdf-text")


def _result(lines: list[OCRLine], pages: int, engine: str) -> OCRResult:
    confs = [l.confidence for l in lines if l.confidence is not None]
    avg = round(sum(confs) / len(confs), 1) if confs else None
    return OCRResult(lines=lines, page_count=pages, engine=engine, average_confidence=avg)
