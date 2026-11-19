"""Writes the diagram file; creates parent folders; refuses to clobber non-.drawio paths."""

from __future__ import annotations

from pathlib import Path

from ..domain.errors import SpecError


class FsWriter:
    def write(self, path: str, content: str) -> str:
        target = Path(path).expanduser()
        if target.suffix.lower() not in (".drawio", ".dio"):
            raise SpecError(f"Output must end in .drawio so VS Code opens it with the draw.io extension (got '{target.name}').")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target.resolve())
