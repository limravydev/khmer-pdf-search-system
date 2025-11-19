# extract_text.py
"""
OCR-only text extraction for Khmer PDF Search System.

For each page:
  1) Render PDF page to image (via pdfplumber).
  2) Preprocess image (grayscale, contrast, resize, denoise, threshold).
  3) Run Tesseract OCR with khm+eng.
  4) Append result to final text.

No digital text extraction is used. Everything comes from OCR.
"""

import pdfplumber
from PIL import Image, ImageFilter, ImageOps

try:
    import pytesseract
    from pytesseract import TesseractError
    HAS_PYTESSERACT = True
except Exception:
    HAS_PYTESSERACT = False
    TesseractError = Exception


# -----------------------------
# Image preprocessing for OCR
# -----------------------------

def preprocess_for_ocr(pil_img: Image.Image) -> Image.Image:
    """
    Improve image quality before sending to Tesseract.

    Steps:
      - convert to grayscale
      - auto-contrast
      - enlarge (2x) if relatively small
      - median filter (denoise)
      - simple threshold to get clear text/background separation
    """
    # 1. grayscale
    img = pil_img.convert("L")

    # 2. auto-contrast
    img = ImageOps.autocontrast(img)

    # 3. upscale if needed (Tesseract likes big text)
    w, h = img.size
    if max(w, h) < 2000:
        img = img.resize((w * 2, h * 2), Image.LANCZOS)

    # 4. denoise
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 5. simple global threshold -> black/white
    img = img.point(lambda x: 0 if x < 180 else 255, mode="1")
    # back to 8-bit grayscale
    img = img.convert("L")

    return img


# -----------------------------
# OCR per page
# -----------------------------

def ocr_page(img: Image.Image) -> str:
    """
    OCR the whole page (Khmer + English) using Tesseract.
    """
    if not HAS_PYTESSERACT:
        return ""

    img = preprocess_for_ocr(img)

    # LSTM only, treat as block of text
    config = "--oem 1 --psm 6"

    try:
        text = pytesseract.image_to_string(img, lang="khm+eng", config=config)
    except TesseractError:
        # fallback: try with default language
        try:
            text = pytesseract.image_to_string(img, config=config)
        except Exception:
            text = ""
    except Exception:
        text = ""

    return text or ""


# -----------------------------
# Public API (used by app.py)
# -----------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF using OCR only.

    For each page:
      - Convert page to image.
      - Run Tesseract OCR (khm+eng).
      - Add header [PAGE n / N – OCR] for debugging.
    """
    if not HAS_PYTESSERACT:
        # No OCR available
        return ""

    labeled_pages = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                page_num = i + 1

                # Render to image
                try:
                    pil_img = page.to_image(resolution=300).original
                except Exception:
                    labeled_pages.append(
                        f"[PAGE {page_num} / {num_pages} – ERROR]\n( failed to render page )"
                    )
                    continue

                # OCR
                text = ocr_page(pil_img).strip()

                header = f"[PAGE {page_num} / {num_pages} – OCR]"
                if text:
                    labeled_pages.append(header + "\n" + text)
                else:
                    labeled_pages.append(header + "\n( no text recognized )")

    except Exception:
        return ""

    return "\n\n".join(labeled_pages)