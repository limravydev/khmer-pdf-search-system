# Khmer PDF Search System

A Streamlit-based NLP application that allows users to upload Khmer PDF
documents, extract text (OCR-friendly), index them with multilingual
sentence embeddings, and search using both **semantic similarity** and
**exact keyword matching**.\
Designed for Khmer-language documents with a simple editor interface for
manual text correction.

## 📌 Features

### ✔ PDF Upload & Text Extraction

-   Upload any Khmer PDF file (scanned or digital)
-   Automatic text extraction via pdfplumber
-   Editable text area for manual correction
-   Download original PDF anytime

### ✔ Intelligent Search

-   Search in **Khmer or English**
-   Hybrid retrieval:
    -   **Exact match first** (with Khmer Unicode normalization)
    -   If no exact match → **semantic similarity**
-   Keyword highlighting in snippet results

### ✔ Document Indexing

-   Uses `distiluse-base-multilingual-cased-v2` (Sentence Transformers)
-   Stores indexed documents in `database/docs.json`
-   Automatically updates documents (no duplicates)

### ✔ Clean Modern UI

-   Two tabs: **Upload & Index** and **Search**
-   Blue buttons inspired by Streamlit theme
-   Search results displayed in attractive cards

## 📂 Project Structure

    khmer_pdf_search/
    │
    ├── app.py
    ├── search_engine.py
    ├── extract_text.py
    ├── database/
    │   └── docs.json
    ├── pdf_storage/
    └── README.md

## 🛠 Installation

### Install dependencies

    pip install streamlit pdfplumber sentence-transformers

Optional OCR support:

    pip install pytesseract pillow

### Run the app

    streamlit run app.py

## 🚀 How to Use

### Upload & Index

1.  Upload a PDF\
2.  Extracted text appears\
3.  Edit the text as needed\
4.  Click **Save & index this document**

### Search

1.  Enter keyword\
2.  Click **Search**\
3.  Exact match → if none → semantic search\
4.  Results show filename, snippet, score, and action buttons

## 🔍 Search Logic

### Exact Match

-   Unicode normalization\
-   Zero-width character cleanup\
-   Matches keyword anywhere in text

### Semantic Search

-   Uses multilingual embeddings\
-   Ranked by cosine similarity

## ⚠️ Limitations

-   OCR quality affects accuracy\
-   PDF may contain inconsistent Khmer character encoding\
-   Browsers restrict embedded PDF viewer

## 💡 Future Improvements

-   Stronger Khmer OCR\
-   Better inline PDF viewer\
-   Topic classification\
-   API backend

## 👨‍🏫 Suitable For

-   University NLP projects\
-   Khmer-language AI research\
-   Enterprise internal search systems
