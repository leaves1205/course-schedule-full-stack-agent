import logging
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.common.exceptions import BusinessException

logger = logging.getLogger(__name__)


def extract_document_text(path: Path) -> str:
    """Extract plain text from supported documents, raising a business exception for empty content or parsing failures."""
    # The database record may exist even if the file has been manually moved from disk.
    if not path.is_file():
        raise BusinessException(message="Document file not found", code=404)
    ext = path.suffix.lower()
    try:
        # Read text files directly; utf-8-sig accepts UTF-8 both with and without a BOM.
        if ext in {".txt", ".md"}:
            text = path.read_text(encoding="utf-8-sig")
        # Extract PDF text page by page, using an empty string for pages without text.
        elif ext == ".pdf":
            with path.open("rb") as source:
                reader = PdfReader(source)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
        # Read DOCX paragraphs and table cells without preserving formatting.
        elif ext == ".docx":
            doc = Document(str(path))
            parts = [p.text for p in doc.paragraphs]
            parts.extend(
                "\t".join(cell.text for cell in row.cells)
                for table in doc.tables
                for row in table.rows
            )
            text = "\n".join(parts)
        # Handle only the four supported formats; legacy .doc files are excluded.
        else:
            raise BusinessException(message="Unsupported document format", code=400)
    except BusinessException:
        raise
    except Exception as exc:
        logger.exception("Failed to extract document text: %s", path.name)
        raise BusinessException(
            message="Unable to read the document. Ensure the file is not corrupted or encrypted and text files use UTF-8 encoding",
            code=400,
        ) from exc

    text = text.strip()
    # Blank documents and scanned files without a text layer cannot provide a text preview.
    if not text:
        raise BusinessException(
            message="No text could be extracted. Blank documents or scanned files cannot be previewed", code=400
        )
    return text
