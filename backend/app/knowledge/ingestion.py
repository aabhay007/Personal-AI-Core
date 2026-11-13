"""Document parsing and text extraction engine."""
import io
import re
from typing import List, Dict, Any
from pypdf import PdfReader
from docx import Document as DocxDocument


def clean_text(text: str) -> str:
    """Normalize whitespace and remove non-printable control characters."""
    if not text:
        return ""
    # Replace carriage returns and excessive whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace multiple spaces with a single space
    text = re.sub(r"[ \t]+", " ", text)
    # Replace 3 or more newlines with 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class DocumentExtractor:
    @staticmethod
    def extract_text(filename: str, data: bytes) -> List[Dict[str, Any]]:
        """Extract text content and page/section metadata from file bytes.
        
        Supported formats: .pdf, .docx, .txt, .md
        """
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if ext == "pdf":
            return DocumentExtractor._extract_pdf(data)
        elif ext in ("docx", "doc"):
            return DocumentExtractor._extract_docx(data)
        elif ext in ("txt", "md", "markdown", "py", "json", "yaml", "yml"):
            return DocumentExtractor._extract_plain_text(data)
        else:
            raise ValueError(f"Unsupported document format '.{ext}'. Supported formats: PDF, DOCX, TXT, MD.")

    @staticmethod
    def _extract_pdf(data: bytes) -> List[Dict[str, Any]]:
        pages = []
        reader = PdfReader(io.BytesIO(data))
        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            cleaned = clean_text(page_text)
            if cleaned:
                pages.append({
                    "content": cleaned,
                    "page_number": idx + 1
                })
        return pages

    @staticmethod
    def _extract_docx(data: bytes) -> List[Dict[str, Any]]:
        doc = DocxDocument(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        cleaned = clean_text(full_text)
        return [{"content": cleaned, "page_number": 1}] if cleaned else []

    @staticmethod
    def _extract_plain_text(data: bytes) -> List[Dict[str, Any]]:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")
        cleaned = clean_text(text)
        return [{"content": cleaned, "page_number": 1}] if cleaned else []
