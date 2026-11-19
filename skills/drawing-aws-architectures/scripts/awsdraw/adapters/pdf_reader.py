"""Reads PDFs. Text comes from poppler's pdftotext, or from the optional `pypdf`
package when poppler is not installed (typical on Windows). Pages are rasterized
with pdftoppm only when the PDF has little or no text layer, so the agent can read
them visually.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from ..domain.documents import DocumentKind, ImageBlob, SourceDocument
from ..domain.errors import DocumentError

MIN_TEXT_CHARS = 80
TIMEOUT_SECONDS = 120
MAX_TEXT_PAGES = 200


def _load_pypdf():
    try:
        from pypdf import PdfReader as PyPdfReader
    except ImportError:
        return None
    return PyPdfReader


class PdfReader:
    suffixes = (".pdf",)

    def __init__(
        self,
        run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        which: Callable[[str], str | None] = shutil.which,
        pypdf_loader: Callable[[], object] = _load_pypdf,
        max_pages: int = 10,
        dpi: int = 100,
    ):
        self._run = run
        self._which = which
        self._pypdf_loader = pypdf_loader
        self._max_pages = max_pages
        self._dpi = dpi

    def read(self, path: str) -> SourceDocument:
        source = Path(path)
        if not source.is_file():
            raise DocumentError(f"File not found: {path}")
        absolute = str(source.resolve())  # absolute paths never look like command-line options

        text = self._extract_text(absolute, source.name)
        warnings: list[str] = []
        images: list[ImageBlob] = []
        if len(text.strip()) < MIN_TEXT_CHARS:
            if self._which("pdftoppm"):
                warnings.append(
                    "The PDF has little or no text layer (scanned or image-only). "
                    f"The first {self._max_pages} pages were rasterized; read them visually."
                )
                images = self._rasterize(absolute, source.name)
            else:
                warnings.append(
                    "The PDF has little or no text layer and 'pdftoppm' (poppler-utils) is not installed, "
                    "so its pages could not be rasterized. Ask the user for the pages as images."
                )
        return SourceDocument(source.name, DocumentKind.PDF, text, tuple(images), tuple(warnings))

    def _extract_text(self, absolute: str, label: str) -> str:
        pdftotext = self._which("pdftotext")
        if pdftotext:
            return self._exec([pdftotext, "-layout", absolute, "-"], label).stdout
        py_reader = self._pypdf_loader()
        if py_reader is None:
            raise DocumentError(
                "No PDF text extractor is available: install poppler-utils (pdftotext) or run "
                "'pip install pypdf'. Alternatively, read the PDF with your IDE agent's own PDF support."
            )
        try:
            pages = py_reader(absolute).pages[:MAX_TEXT_PAGES]
            return "\n\n".join((page.extract_text() or "") for page in pages)
        except Exception as exc:  # pypdf raises many error types for damaged files
            raise DocumentError(f"Could not read {label} with pypdf: {exc}.") from None

    def _exec(self, command: list[str], label: str) -> subprocess.CompletedProcess:
        try:
            done = self._run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
        except subprocess.TimeoutExpired:
            raise DocumentError(f"Reading {label} took longer than {TIMEOUT_SECONDS}s; split the PDF and retry.") from None
        if done.returncode != 0:
            detail = (done.stderr or "").strip().splitlines()[:1]
            raise DocumentError(f"Could not read {label}: {detail[0] if detail else 'unknown error'}.")
        return done

    def _rasterize(self, absolute: str, label: str) -> list[ImageBlob]:
        pdftoppm = self._which("pdftoppm")
        with tempfile.TemporaryDirectory() as tmp:
            prefix = str(Path(tmp) / "page")
            self._exec(
                [pdftoppm, "-png", "-r", str(self._dpi), "-f", "1", "-l", str(self._max_pages), absolute, prefix],
                label,
            )
            return [ImageBlob(f.name, f.read_bytes()) for f in sorted(Path(tmp).glob("page*.png"))]
