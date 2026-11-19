"""Opens a file in VS Code through its `code` command line launcher, if present."""

from __future__ import annotations

import shutil
import subprocess
from typing import Callable


class VsCodeOpener:
    def __init__(self, which: Callable[[str], str | None] = shutil.which, run: Callable = subprocess.run):
        self._which, self._run = which, run

    def open(self, path: str) -> bool:
        code = self._which("code")
        if not code:
            return False
        try:
            self._run([code, "--reuse-window", path], check=False, timeout=15, capture_output=True)
        except (OSError, subprocess.TimeoutExpired):
            return False
        return True
