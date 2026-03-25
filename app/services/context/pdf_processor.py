"""PDF and document text extraction and chunking."""

import io
import logging
import re
from typing import Iterator

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(content: bytes) -> str:
    """
    Extract text from a PDF file.

    Args:
        content: PDF file content as bytes

    Returns:
        Extracted text as a single string
    """
    reader = PdfReader(io.BytesIO(content))
    text_parts = []

    for page_num, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            text_parts.append(text)
        except Exception as e:
            logger.warning("Failed to extract text from page %d: %s", page_num, e)

    return "\n\n".join(text_parts)


def extract_text_from_txt(content: bytes) -> str:
    """Extract text from a plain text file."""
    # Try common encodings
    for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue

    # Fall back to utf-8 with replacement
    return content.decode("utf-8", errors="replace")


def extract_text_from_markdown(content: bytes) -> str:
    """Extract text from a Markdown file."""
    return extract_text_from_txt(content)


def extract_text(content: bytes, file_type: str) -> str:
    """
    Extract text from a document based on file type.

    Args:
        content: File content as bytes
        file_type: File type (pdf, txt, md)

    Returns:
        Extracted text
    """
    extractors = {
        "pdf": extract_text_from_pdf,
        "txt": extract_text_from_txt,
        "md": extract_text_from_markdown,
    }

    extractor = extractors.get(file_type)
    if not extractor:
        raise ValueError(f"Unsupported file type: {file_type}")

    return extractor(content)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: list[str] | None = None,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Text to split
        chunk_size: Maximum characters per chunk
        chunk_overlap: Number of characters to overlap between chunks
        separators: List of separators to try splitting on (default: paragraphs, sentences)

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    if separators is None:
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    # Clean up text
    text = re.sub(r"\s+", " ", text).strip()

    chunks = []
    current_chunk = ""

    # Split by separators
    parts = _split_by_separators(text, separators)

    for part in parts:
        # If adding this part exceeds chunk size, save current chunk
        if current_chunk and len(current_chunk) + len(part) > chunk_size:
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap from previous
            if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                current_chunk = current_chunk[-chunk_overlap:] + part
            else:
                current_chunk = part
        else:
            current_chunk += part

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _split_by_separators(text: str, separators: list[str]) -> Iterator[str]:
    """Split text by separators, keeping separators attached to preceding text."""
    if not separators:
        yield text
        return

    sep = separators[0]
    remaining_seps = separators[1:]

    parts = text.split(sep)

    for i, part in enumerate(parts):
        if remaining_seps and len(part) > 500:
            # Recursively split with next separator
            yield from _split_by_separators(part, remaining_seps)
        else:
            yield part

        # Add separator back (except for last part)
        if i < len(parts) - 1:
            yield sep


def get_chunk_metadata(
    chunk: str,
    chunk_index: int,
    document_id: str,
    filename: str,
    total_chunks: int,
) -> dict:
    """Create metadata for a chunk."""
    return {
        "document_id": document_id,
        "filename": filename,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "char_count": len(chunk),
    }
