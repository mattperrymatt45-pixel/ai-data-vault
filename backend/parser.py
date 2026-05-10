"""
Document Parser Module
Supports: PDF, DOCX, TXT, MD, HTML
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any


def parse_document(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """
    Parse a document and return a list of chunks with metadata.
    Each chunk is a dict: { "text": str, "metadata": { "source": str, "page": int, "chunk_index": int } }
    """
    ext = Path(filename).suffix.lower()
    
    if ext == ".pdf":
        return parse_pdf(file_path, filename)
    elif ext == ".docx":
        return parse_docx(file_path, filename)
    elif ext in [".txt", ".md", ".markdown"]:
        return parse_text(file_path, filename)
    elif ext in [".html", ".htm"]:
        return parse_html(file_path, filename)
    else:
        # Try as plain text fallback
        return parse_text(file_path, filename)


def parse_pdf(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """Parse PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        chunks = []
        doc = fitz.open(file_path)
        
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                page_chunks = chunk_text(text, chunk_size=800, overlap=100)
                for i, chunk in enumerate(page_chunks):
                    chunks.append({
                        "text": chunk,
                        "metadata": {
                            "source": filename,
                            "page": page_num,
                            "chunk_index": i,
                            "type": "pdf"
                        }
                    })
        
        doc.close()
        return chunks
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")


def parse_docx(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """Parse DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(file_path)
        
        full_text = "\n\n".join(
            para.text for para in doc.paragraphs if para.text.strip()
        )
        
        page_chunks = chunk_text(full_text, chunk_size=800, overlap=100)
        return [
            {
                "text": chunk,
                "metadata": {
                    "source": filename,
                    "page": i + 1,
                    "chunk_index": i,
                    "type": "docx"
                }
            }
            for i, chunk in enumerate(page_chunks)
        ]
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX: {e}")


def parse_text(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """Parse plain text / markdown files."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        
        # Strip markdown syntax for cleaner embedding
        ext = Path(filename).suffix.lower()
        if ext in [".md", ".markdown"]:
            text = strip_markdown(text)
        
        page_chunks = chunk_text(text, chunk_size=800, overlap=100)
        return [
            {
                "text": chunk,
                "metadata": {
                    "source": filename,
                    "page": i + 1,
                    "chunk_index": i,
                    "type": "text"
                }
            }
            for i, chunk in enumerate(page_chunks)
        ]
    except Exception as e:
        raise ValueError(f"Failed to parse text file: {e}")


def parse_html(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """Parse HTML using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "lxml")
        
        # Remove script/style tags
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        
        text = soup.get_text(separator="\n")
        page_chunks = chunk_text(text, chunk_size=800, overlap=100)
        return [
            {
                "text": chunk,
                "metadata": {
                    "source": filename,
                    "page": i + 1,
                    "chunk_index": i,
                    "type": "html"
                }
            }
            for i, chunk in enumerate(page_chunks)
        ]
    except Exception as e:
        raise ValueError(f"Failed to parse HTML: {e}")


def strip_markdown(text: str) -> str:
    """Remove common markdown syntax."""
    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # Remove inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove images
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)
    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    return text


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks, respecting sentence boundaries.
    """
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    # Split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_len = len(sentence)
        
        if current_size + sentence_len > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Overlap: keep last few sentences
            overlap_text = " ".join(current_chunk)
            if len(overlap_text) > overlap:
                overlap_text = overlap_text[-overlap:]
            current_chunk = [overlap_text] if overlap_text.strip() else []
            current_size = len(overlap_text)
        
        current_chunk.append(sentence)
        current_size += sentence_len + 1
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return [c for c in chunks if c.strip()]
