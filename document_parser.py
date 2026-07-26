from pathlib import Path
from typing import Any

import PyPDF2

class DocumentParser:
    """
    Parses scientific papers (PDFs) to extract text and metadata.
    Uses PyPDF2 for permissive open-source compatibility.
    """

    def __init__(self):
        pass

    def parse(self, pdf_path: str | Path) -> str:
        """Extracts all text content from the PDF."""
        path = Path(pdf_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        text_content = []
        try:
            # Open document securely using context manager
            with open(path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    # extract_text handles standard text extraction
                    text = page.extract_text()
                    if text:
                        text_content.append(text)

            return "\n\n".join(text_content)
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"

    def extract_metadata(self, pdf_path: str | Path) -> dict[str, Any]:
        """Extracts metadata from the PDF (e.g., Title, Author, Page Count)."""
        path = Path(pdf_path).expanduser()
        if not path.exists():
            return {"error": "File not found"}

        try:
            with open(path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata

                # Clean and structure the metadata dictionary
                clean_metadata = {
                    "title": metadata.title if metadata and metadata.title else "",
                    "author": metadata.author if metadata and metadata.author else "",
                    "subject": metadata.subject if metadata and metadata.subject else "",
                    "keywords": metadata.get("/Keywords", "") if metadata else "",
                    "page_count": len(reader.pages)
                }
                return clean_metadata
        except Exception as e:
            return {"error": f"Failed to extract metadata: {str(e)}"}
