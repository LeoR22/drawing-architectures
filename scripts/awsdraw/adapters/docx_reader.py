"""Reads .docx files with the standard library only.

Input is untrusted: members are read one by one with size caps (never extracted
to disk), and XML containing DOCTYPE or ENTITY declarations is refused.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from ..domain.documents import DocumentKind, ImageBlob, SourceDocument
from ..domain.errors import DocumentError

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_XML_BYTES = 30 * 1024 * 1024
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_IMAGES = 40
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _read_member(zf: zipfile.ZipFile, member: str, limit: int) -> bytes | None:
    try:
        info = zf.getinfo(member)
    except KeyError:
        return None
    if info.file_size > limit:
        raise DocumentError(f"'{member}' is larger than {limit // (1024 * 1024)} MB; refusing to read it.")
    with zf.open(info) as fh:
        data = fh.read(limit + 1)
    if len(data) > limit:
        raise DocumentError(f"'{member}' is larger than {limit // (1024 * 1024)} MB; refusing to read it.")
    return data


def _paragraph_text(p: ET.Element) -> str:
    parts = []
    for node in p.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag in (W + "tab", W + "br"):
            parts.append(" ")
    return "".join(parts).strip()


def _paragraph(p: ET.Element) -> str:
    text = _paragraph_text(p)
    if not text:
        return ""
    props = p.find(W + "pPr")
    if props is not None:
        style = props.find(W + "pStyle")
        style_id = style.get(W + "val", "") if style is not None else ""
        heading = re.match(r"(?i)heading\s*(\d)", style_id)
        if heading:
            return "#" * min(int(heading.group(1)), 6) + " " + text
        if style_id.lower() == "title":
            return "# " + text
        if props.find(W + "numPr") is not None:
            return "- " + text
    return text


def _table(tbl: ET.Element) -> str:
    rows = []
    for tr in tbl.findall(W + "tr"):
        cells = [
            " ".join(filter(None, (_paragraph_text(p) for p in tc.iter(W + "p")))).replace("|", "/")
            for tc in tr.findall(W + "tc")
        ]
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(r) + " |" for r in rows]
    lines.insert(1, "|" + "---|" * width)
    return "\n".join(lines)


class DocxReader:
    suffixes = (".docx",)

    def read(self, path: str) -> SourceDocument:
        name = Path(path).name
        try:
            zf = zipfile.ZipFile(path)
        except FileNotFoundError:
            raise DocumentError(f"File not found: {path}") from None
        except (zipfile.BadZipFile, IsADirectoryError):
            raise DocumentError(f"{name} is not a valid .docx file (it is not a zip package).") from None

        with zf:
            xml = _read_member(zf, "word/document.xml", MAX_XML_BYTES)
            if xml is None:
                raise DocumentError(f"{name} has no word/document.xml; it does not look like a Word document.")
            if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                raise DocumentError(f"{name} contains an XML DOCTYPE/ENTITY declaration; refusing to parse it.")
            try:
                root = ET.fromstring(xml)
            except ET.ParseError as exc:
                raise DocumentError(f"{name}: invalid document XML ({exc}).") from None

            body = root.find(W + "body")
            blocks = []
            for element in body if body is not None else []:
                block = _paragraph(element) if element.tag == W + "p" else _table(element) if element.tag == W + "tbl" else ""
                if block:
                    blocks.append(block)
            text = "\n\n".join(blocks)

            images, warnings = self._images(zf)

        if not text.strip():
            warnings.append("No text found in the document body; the content may be in embedded images.")
        return SourceDocument(name, DocumentKind.DOCX, text, tuple(images), tuple(warnings))

    @staticmethod
    def _images(zf: zipfile.ZipFile) -> tuple[list[ImageBlob], list[str]]:
        images: list[ImageBlob] = []
        warnings: list[str] = []
        for member in sorted(n for n in zf.namelist() if n.startswith("word/media/")):
            base = member.rsplit("/", 1)[-1]
            if Path(base).suffix.lower() not in IMAGE_SUFFIXES:
                warnings.append(f"Skipped embedded file '{base}' (unsupported image type); describe it manually if it matters.")
                continue
            if len(images) >= MAX_IMAGES:
                warnings.append(f"Stopped after {MAX_IMAGES} embedded images.")
                break
            try:
                data = _read_member(zf, member, MAX_IMAGE_BYTES)
            except DocumentError as exc:
                warnings.append(str(exc))
                continue
            if data:
                images.append(ImageBlob(base, data))
        return images, warnings
