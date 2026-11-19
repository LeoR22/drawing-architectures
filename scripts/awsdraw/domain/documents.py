"""Entities for use-case documents supplied by the user. Pure Python."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DocumentKind(str, Enum):
    TEXT = "text"
    DOCX = "docx"
    PDF = "pdf"
    IMAGE = "image"


@dataclass(frozen=True)
class ImageBlob:
    name: str
    data: bytes


@dataclass(frozen=True)
class SourceDocument:
    name: str
    kind: DocumentKind
    text: str  # Markdown-ish plain text; empty for images
    images: tuple[ImageBlob, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractionResult:
    name: str
    kind: DocumentKind
    directory: str
    characters: int
    images: tuple[str, ...]
    warnings: tuple[str, ...]
