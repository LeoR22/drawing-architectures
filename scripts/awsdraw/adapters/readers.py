"""Turns an uploaded/attached file into text (+ images) with the right reader."""

from __future__ import annotations

from pathlib import Path

from ..domain.documents import SourceDocument
from ..domain.errors import DocumentError
from .docx_reader import DocxReader
from .image_reader import ImageReader
from .pdf_reader import PdfReader
from .text_reader import TextReader

_READERS = (TextReader(), DocxReader(), PdfReader(), ImageReader())


def read_document(path: str) -> SourceDocument:
    suffix = Path(path).suffix.lower()
    for reader in _READERS:
        if suffix in reader.suffixes:
            return reader.read(path)
    supported = ", ".join(s for r in _READERS for s in r.suffixes)
    raise DocumentError(f"Unsupported file type '{suffix}'. Supported: {supported}.")
