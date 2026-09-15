import os
import fitz  # PyMuPDF
from docx import Document

def load_pdf(file_path):
    """Extract text from a PDF file."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"Error loading PDF {file_path}: {e}")
    return text

def load_docx(file_path):
    """Extract text from a DOCX file."""
    text = ""
    try:
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error loading DOCX {file_path}: {e}")
    return text

def load_txt(file_path):
    """Extract text from a TXT file."""
    text = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"Error loading TXT {file_path}: {e}")
    return text

def load_document(file_path):
    """
    Load a document based on its extension.
    Returns a dictionary with 'content' and 'metadata'.
    """
    ext = os.path.splitext(file_path)[1].lower()
    content = ""
    
    if ext == ".pdf":
        content = load_pdf(file_path)
    elif ext in [".doc", ".docx"]:
        content = load_docx(file_path)
    elif ext == ".txt":
        content = load_txt(file_path)
    else:
        print(f"Unsupported file format: {ext} for file {file_path}")
        return None
        
    if not content.strip():
        return None

    filename = os.path.basename(file_path)
    metadata = {
        "source": filename,
        "extension": ext
    }
    
    return {"content": content, "metadata": metadata}
