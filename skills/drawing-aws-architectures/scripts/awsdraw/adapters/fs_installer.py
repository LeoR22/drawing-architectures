"""Installs this skill for VS Code (GitHub Copilot agent skills / Claude skills) and recommends the draw.io extension."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..domain.errors import SpecError

EXTENSION_ID = "hediet.vscode-drawio"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "tests", ".git")
PROJECT_TARGETS = {"copilot": ".github/skills", "claude": ".claude/skills", "agents": ".agents/skills"}
USER_TARGETS = {"copilot": ".copilot/skills", "claude": ".claude/skills", "agents": ".agents/skills"}


class FsInstaller:
    def install(self, skill_root: Path, name: str, scope: str, flavor: str, project: str | None) -> Path:
        if flavor not in PROJECT_TARGETS:
            raise SpecError(f"Unknown target '{flavor}'. Use one of: {', '.join(PROJECT_TARGETS)}.")
        if scope == "user":
            base = Path.home() / USER_TARGETS[flavor]
        elif scope == "project":
            base = Path(project or ".").resolve() / PROJECT_TARGETS[flavor]
        else:
            raise SpecError("Scope must be 'project' or 'user'.")
        dest = base / name
        if dest.resolve() == skill_root.resolve():
            raise SpecError("The skill is already installed at that location.")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_root, dest, ignore=IGNORE)
        if scope == "project":
            self._recommend_extension(Path(project or ".").resolve())
        return dest

    @staticmethod
    def _recommend_extension(project: Path) -> None:
        path = project / ".vscode" / "extensions.json"
        data: dict = {}
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return  # do not touch a file we cannot parse (it may hold comments)
        recs = list(data.get("recommendations", []))
        if EXTENSION_ID not in recs:
            recs.append(EXTENSION_ID)
        data["recommendations"] = recs
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
