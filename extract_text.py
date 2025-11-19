# extract_text.py
"""
OCR-only text extraction for Khmer PDF Search System,
with Tesseract orientation detection + robust fallback.

Steps per page:
  1) Render PDF page to image (via pdfplumber).
  2) Use Tesseract OSD (image_to_osd) to detect rotation.
  3) Rotate accordingly and OCR.
  4) Also try a few candidate angles (0, 90, 270, 180) and
     choose the best by a simple text score.

Everything is OCR – we do not use pdfplumber text extraction.
"""

import pdfplumber
from PIL import Image, ImageFilter, ImageOps

try:
    import pytesseract
    from pytesseract import TesseractError, Output
    HAS_PYTESSERACT = True
except Exception:
    HAS_PYTESSERACT = False
    TesseractError = Exception
    Output = None


# -----------------------------
# Character helpers (scoring)
# -----------------------------

def is_khmer(ch: str) -> bool:
    return 0x1780 <= ord(ch) <= 0x17FF


def count_khmer(text: str) -> int:
    return sum(is_khmer(c) for c in text)


def count_latin(text: str) -> int:
    return sum(c.isascii() and c.isalpha() for c in text)


def score_text(text: str) -> int:
    """
    Simple score of OCR quality: number of Khmer + Latin letters.
    Higher -> more like real text.
    """
    if not text:
        return 0
    return count_khmer(text) + count_latin(text)


# -----------------------------
# Preprocessing
# -----------------------------

def preprocess_for_ocr(pil_img: Image.Image) -> Image.Image:
    """Enhance image quality before OCR."""
    img = pil_img.convert("L")  # grayscale
    img = ImageOps.autocontrast(img)

    w, h = img.size
    if max(w, h) < 2000:
        img = img.resize((w * 2, h * 2), Image.LANCZOS)

    img = img.filter(ImageFilter.MedianFilter(size=3))

    # threshold
    img = img.point(lambda x: 0 if x < 180 else 255, mode="1")
    img = img.convert("L")
    return img


# -----------------------------
# Core OCR helpers
# -----------------------------

def run_ocr_once(pil_img: Image.Image, angle: int) -> tuple[str, int]:
    """
    Rotate → preprocess → OCR → score.
    Returns (text, score).
    """
    if angle != 0:
        pil_img = pil_img.rotate(angle, expand=True)

    img = preprocess_for_ocr(pil_img)

    config = "--oem 1 --psm 6"
    try:
        text = pytesseract.image_to_string(img, lang="khm+eng", config=config)
    except Exception:
        text = ""

    text = text.strip()
    return text, score_text(text)


def detect_osd_angle(pil_img: Image.Image) -> int:
    """
    Use Tesseract OSD (orientation & script detection) to guess the rotation.
    Returns one of {0, 90, 180, 270}.
    """
    if not (HAS_PYTESSERACT and Output is not None):
        return 0

    try:
        osd = pytesseract.image_to_osd(pil_img, output_type=Output.DICT)
        angle = int(osd.get("rotate", 0))
        # Tesseract gives angle as 0/90/180/270 degrees clockwise.
        # To deskew we need to rotate counter-clockwise:
        angle = (-angle) % 360
        if angle in (0, 90, 180, 270):
            return angle
        return 0
    except Exception:
        return 0


def ocr_page_smart(pil_img: Image.Image) -> tuple[str, int]:
    """
    Combine OSD detection + trying a few angles.
    Returns (best_text, best_angle).
    """
    # 1) Ask Tesseract for rotation
    osd_angle = detect_osd_angle(pil_img)

    # Start with the OSD suggestion
    candidate_angles = []
    if osd_angle in (0, 90, 180, 270):
        candidate_angles.append(osd_angle)

    # Add remaining angles as fallbacks
    for a in (0, 90, 270, 180):
        if a not in candidate_angles:
            candidate_angles.append(a)

    best_text = ""
    best_score = -1
    best_angle = 0

    for angle in candidate_angles:
        text, score = run_ocr_once(pil_img, angle)
        if score > best_score:
            best_score = score
            best_text = text
            best_angle = angle

    return best_text, best_angle


# -----------------------------
# Public API used by app.py
# -----------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF using OCR only,
    with orientation detection and fallback.

    Output includes headers like:
      [PAGE 1/3 – OCR angle=90°]
    so you can see what was chosen.
    """
    if not HAS_PYTESSERACT:
        return ""

    pages_output = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                page_num = i + 1

                # Render page to image
                try:
                    pil_img = page.to_image(resolution=300).original
                except Exception:
                    pages_output.append(
                        f"[PAGE {page_num}/{num_pages} – ERROR]\n( failed to render page )"
                    )
                    continue

                # OCR with smart orientation handling
                text, angle = ocr_page_smart(pil_img)
                if not text:
                    text = "( no text recognized )"

                pages_output.append(
                    f"[PAGE {page_num}/{num_pages} – OCR angle={angle}°]\n{text}"
                )

    except Exception:
        return ""

    return "\n\n".join(pages_output)