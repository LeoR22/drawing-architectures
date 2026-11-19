"""Reads plain text and Markdown use cases."""

from __future__ import annotations

from pathlib import Path

from ..domain.documents import DocumentKind, SourceDocument
from ..domain.errors import DocumentError

MAX_BYTES = 2 * 1024 * 1024


class TextReader:
    suffixes = (".txt", ".md")

    def read(self, path: str) -> SourceDocument:
        source = Path(path)
        if not source.is_file():
            raise DocumentError(f"File not found: {path}")
        if source.stat().st_size > MAX_BYTES:
            raise DocumentError(f"{source.name} is larger than {MAX_BYTES // (1024 * 1024)} MB; split it and retry.")
        return SourceDocument(source.name, DocumentKind.TEXT, source.read_text(encoding="utf-8", errors="replace"))
