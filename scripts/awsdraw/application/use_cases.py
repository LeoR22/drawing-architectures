"""Use cases: orchestrate domain + ports. No I/O details here."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain import layout as layout_mod
from ..domain.errors import SpecError
from ..domain.models import Architecture, Finding, Requirements
from ..domain.rules import has_errors, validate
from .ports import DiagramRenderer, EditorOpener, FileWriter, Planner


@dataclass(frozen=True)
class DiagramResult:
    architecture: Architecture
    xml: str
    layout: layout_mod.Layout
    findings: tuple[Finding, ...] = field(default_factory=tuple)


class GenerateDiagram:
    """Validated Architecture -> draw.io XML."""

    def __init__(self, renderer: DiagramRenderer):
        self._renderer = renderer

    def __call__(self, arch: Architecture) -> DiagramResult:
        findings = validate(arch)
        if has_errors(findings):
            raise SpecError("; ".join(f"{f.code}: {f.message}" for f in findings if f.severity == "error"))
        lay = layout_mod.compute(arch)
        return DiagramResult(arch, self._renderer.render(arch, lay), lay, tuple(findings))


class PlanAndGenerate:
    """Requirements -> Architecture (via a Planner) -> draw.io XML."""

    def __init__(self, planner: Planner, generate: GenerateDiagram, fallback: Planner | None = None):
        self._planner, self._generate, self._fallback = planner, generate, fallback

    def __call__(self, req: Requirements) -> DiagramResult:
        try:
            return self._generate(self._planner.plan(req))
        except SpecError:
            if self._fallback is None:
                raise
            return self._generate(self._fallback.plan(req))


class SaveDiagram:
    def __init__(self, writer: FileWriter, opener: EditorOpener | None = None):
        self._writer, self._opener = writer, opener

    def __call__(self, result: DiagramResult, path: str, open_in_editor: bool = False) -> tuple[str, bool]:
        saved = self._writer.write(path, result.xml)
        opened = bool(open_in_editor and self._opener and self._opener.open(saved))
        return saved, opened


class CollectRequirements:
    """Free text + document paths -> Requirements (text from docs is appended; images are kept for vision planners)."""

    def __init__(self, read_document):
        self._read = read_document

    def __call__(self, text: str, paths: list[str]) -> tuple[Requirements, list[str]]:
        parts = [text.strip()] if text.strip() else []
        images: list[tuple[str, bytes]] = []
        warnings: list[str] = []
        for path in paths:
            doc = self._read(path)
            if doc.text.strip():
                parts.append(doc.text.strip())
            images.extend((img.name, img.data) for img in doc.images)
            warnings.extend(f"{doc.name}: {w}" for w in doc.warnings)
        if not parts and not images:
            raise SpecError("Provide the use case as text or attach a PDF, Word, text or image file.")
        return Requirements("\n\n".join(parts), tuple(images)), warnings
