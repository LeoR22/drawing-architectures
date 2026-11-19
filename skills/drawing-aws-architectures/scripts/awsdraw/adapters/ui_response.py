"""Builds the JSON-able response shown by the UI (shared by the local server and the in-browser engine)."""

from __future__ import annotations

import time

from ..application.use_cases import DiagramResult
from . import svg_preview


def to_response(result: DiagramResult, used: str, warnings: list[str], started: float) -> dict:
    arch = result.architecture
    name = "".join(ch if ch.isalnum() else "-" for ch in arch.title.lower()).strip("-")[:40] or "architecture"
    return {
        "title": arch.title, "planner": used, "filename": f"{name}.drawio",
        "xml": result.xml, "svg": svg_preview.render(arch, result.layout),
        "components": [{"id": c.id, "service": c.service, "label": c.label} for c in arch.components],
        "warnings": warnings + [f"{f.code}: {f.message}" for f in result.findings],
        "seconds": round(time.perf_counter() - started, 2),
    }
