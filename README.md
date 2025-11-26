# Khmer PDF Search System  
AUPP – NLP Course Project  

A Streamlit application that extracts text from Khmer PDF documents using OCR, indexes them using vector embeddings, and provides fast keyword + semantic search.  
The system includes a built-in PDF previewer, an editable OCR text panel, and a document management interface.

---

## 🚀 Features

### **1. Khmer OCR (Optical Character Recognition)**
- Extracts text from scanned Khmer PDFs  
- Uses Tesseract OCR (with Khmer traineddata when available)  
- Robust fallback handling if Khmer OCR is not supported in the environment  
- Page-by-page OCR for higher accuracy

### **2. Scrollable PDF Preview (Image-based)**
- Secure PDF rendering using `pdfplumber`  
- Avoids Chrome PDF-plugin blocking  
- Clean viewer with:
  - Vertical scroll
  - Rounded border
  - Page selector

### **3. Editable OCR Text Panel**
- Side-by-side layout: left = PDF preview, right = OCR text  
- Users can correct OCR mistakes manually  
- Updated text can be re-indexed instantly

### **4. Semantic Search Engine**
- Uses Sentence-Transformers embeddings  
- FAISS CPU index for fast similarity search  
- Supports Khmer and English queries  
- Highlights exact text matches  
- Returns both semantic matches and literal keyword matches

### **5. PDF Management**
- Upload new PDFs  
- Automatically OCR + index on upload  
- Open existing documents  
- Re-index after manual edits  
- Clean detection of missing/removed PDF files

---

## 🛠 Tech Stack

| Component | Library |
|----------|---------|
| UI | Streamlit |
| OCR | Pytesseract + Tesseract-OCR |
| PDF Rendering | pdfplumber + Pillow |
| Embeddings | Sentence-Transformers |
| Vector Index | FAISS CPU |
| Storage | JSON-based local index |

---

## 📁 Project Structure

```
khmer-pdf-search-system/
│
├── app.py                 # Main Streamlit UI
├── extract_text.py        # OCR pipeline (with fallback)
├── search_engine.py       # Embedding + search engine
├── requirements.txt       # Python dependencies
├── packages.txt           # System dependencies (Tesseract)
├── pdf_storage/           # Uploaded PDF files
└── docs.json              # Indexed text + embeddings
```

---

## 📦 Installation (Local)

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/khmer-pdf-search-system.git
cd khmer-pdf-search-system
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Tesseract-OCR

**macOS**
```bash
brew install tesseract
brew install tesseract-lang
```

**Ubuntu**
```bash
sudo apt install tesseract-ocr tesseract-ocr-khm
```

### 4. Run the app
```bash
streamlit run app.py
```

---

## 🌐 Deployment

### **Streamlit Cloud**
Requires:
- `requirements.txt` (Python deps)
- `packages.txt` (system deps)

Your `packages.txt` should contain:

```
tesseract-ocr
tesseract-ocr-khm
```

### **Hugging Face Spaces (Recommended)**
Supports:
- Streamlit app
- `requirements.txt`
- `apt.txt` equivalent (same as packages.txt)

---

## 🧪 How It Works

### 1. **User uploads PDF**
- File saved to `/pdf_storage`
- OCR runs on each page
- Extracted text is indexed immediately

### 2. **User edits OCR text**
- Updates are saved
- Re-indexed using Sentence-Transformer embeddings

### 3. **Search**
- Query is embedded
- FAISS finds similar documents
- Exact keyword matches are highlighted

---

## 📸 Screenshots
(Add screenshots here later)

---

## 👨‍💻 Author
**Ravy Lim**  
Master of Science in AI, AUPP  
GitHub: https://github.com/limravydev

---

## 📄 License
This project is for educational and academic use under AUPP’s NLP course.  
You may use or extend it with attribution.
