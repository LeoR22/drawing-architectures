"""Passes images through so the agent can view them; checks the file really is an image."""

from __future__ import annotations

from pathlib import Path

from ..domain.documents import DocumentKind, ImageBlob, SourceDocument
from ..domain.errors import DocumentError

MAX_BYTES = 20 * 1024 * 1024
SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a")


def _looks_like_image(data: bytes) -> bool:
    return data.startswith(SIGNATURES) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")


class ImageReader:
    suffixes = (".png", ".jpg", ".jpeg", ".gif", ".webp")

    def read(self, path: str) -> SourceDocument:
        source = Path(path)
        if not source.is_file():
            raise DocumentError(f"File not found: {path}")
        if source.stat().st_size > MAX_BYTES:
            raise DocumentError(f"{source.name} is larger than {MAX_BYTES // (1024 * 1024)} MB; resize it and retry.")
        data = source.read_bytes()
        if not _looks_like_image(data):
            raise DocumentError(f"{source.name} has an image extension but its content is not PNG, JPEG, GIF or WebP.")
        return SourceDocument(
            source.name,
            DocumentKind.IMAGE,
            "",
            (ImageBlob(source.name, data),),
            ("Images carry no text layer: view the image and transcribe components, labels and arrows into the requirements.",),
        )
