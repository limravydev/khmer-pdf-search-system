# extract_text.py
import io
from typing import Optional

import pdfplumber
from PIL import Image

try:
    import pytesseract
    from pytesseract import TesseractError
    HAS_PYTESSERACT = True
except Exception:
    HAS_PYTESSERACT = False
    TesseractError = Exception  # dummy


def ocr_image(img: Image.Image) -> str:
    """
    Run OCR on a PIL image, trying Khmer first,
    then falling back to default Tesseract language.
    Never raises TesseractError.
    """
    if not HAS_PYTESSERACT:
        return ""

    # Common config: treat as block of text
    config = "--psm 6"

    # 1) Try Khmer language (if available)
    for lang in ["khm", None]:  # None = Tesseract default (often eng)
        try:
            if lang is None:
                text = pytesseract.image_to_string(img, config=config)
            else:
                text = pytesseract.image_to_string(img, lang=lang, config=config)
            if text:
                return text
        except TesseractError:
            # If lang is missing or Tesseract fails, try next option
            continue
        except Exception:
            continue

    return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF using OCR for each page.
    Returns a single string with all pages concatenated.
    Never raises if OCR fails.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texts = []
            for page in pdf.pages:
                # Render page as image
                page_img = page.to_image(resolution=300).original
                # Ensure it's a PIL Image
                if not isinstance(page_img, Image.Image):
                    page_img = Image.fromarray(page_img)
                page_text = ocr_image(page_img)
                texts.append(page_text)
    except Exception:
        return ""

    return "\n\n".join(t.strip() for t in texts if t.strip())