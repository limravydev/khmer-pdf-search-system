# extract_text.py
"""
Khmer OCR-based text extraction for PDF files.

This module uses:
- pdfplumber  : to open PDF and render pages as images
- pytesseract : to perform OCR with Khmer language model ("khm")

Usage:
    from extract_text import extract_text_from_pdf
    text = extract_text_from_pdf("path/to/file.pdf")
"""

import pdfplumber
import pytesseract
from PIL import Image, ImageFilter, ImageOps


def ocr_page(page, dpi: int = 400) -> str:
    """
    Render a single PDF page to an image and run Khmer OCR on it.

    Args:
        page: pdfplumber.page.Page object
        dpi: resolution used to render the page (higher = slower but clearer)

    Returns:
        OCR'd text for that page as a string.
    """
    # Render the page as a high-resolution PIL image
    img: Image.Image = page.to_image(resolution=dpi).original

    # --- Basic preprocessing to help Tesseract ---
    # 1) Convert to grayscale
    img = img.convert("L")

    # 2) Auto-contrast to improve text visibility
    img = ImageOps.autocontrast(img)

    # 3) Apply a small median filter to reduce noise
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Tesseract OCR configuration:
    # --psm 6 : Assume a uniform block of text
    # --oem 3 : Default LSTM OCR engine
    config = "--psm 6 --oem 3"

    # Run OCR with Khmer language model
    text = pytesseract.image_to_string(img, lang="khm", config=config)

    return text


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file using pure Khmer OCR on each page.

    This version does *not* rely on PDF's embedded text; it always uses OCR.
    That is safer for scanned PDFs and matches the requirement "use OCR".

    Args:
        pdf_path: path to PDF file

    Returns:
        Full text of the PDF (all pages concatenated).
    """
    texts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = ocr_page(page)
            texts.append(page_text)

    return "\n".join(texts)