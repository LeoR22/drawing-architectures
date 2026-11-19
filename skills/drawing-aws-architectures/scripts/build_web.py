"""Builds the static site (docs/): index.html + awsdraw.zip, the Python package the browser runs via Pyodide.

Usage: python scripts/build_web.py [--out DIR]   (default: <repository root>/docs)
The zip is deterministic (sorted entries, fixed timestamps) so tests can check it is up to date.
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
PKG = SKILL_ROOT / "scripts" / "awsdraw"
PYODIDE_VERSION = "0.29.5"
# Modules that need a real OS, sockets or a terminal never ship to the browser.
EXCLUDE = {
    "cli.py", "adapters/web_ui.py", "adapters/fs_installer.py", "adapters/fs_writer.py",
    "adapters/vscode_opener.py", "adapters/llm_anthropic.py", "adapters/llm_github.py",
}


def package_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PKG.rglob("*.py")):
            rel = path.relative_to(PKG).as_posix()
            if rel in EXCLUDE or "__pycache__" in rel:
                continue
            info = zipfile.ZipInfo(f"awsdraw/{rel}", date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return buffer.getvalue()


def page_html() -> str:
    html = (PKG / "adapters" / "ui_page.html").read_text(encoding="utf-8")
    return html.replace("__PROVIDERS__", "null").replace("__PYODIDE_VERSION__", PYODIDE_VERSION)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(SKILL_ROOT.parents[1] / "docs"))
    out = Path(parser.parse_args(argv).out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "awsdraw.zip").write_bytes(package_zip())
    (out / "index.html").write_text(page_html(), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built {out}/index.html and awsdraw.zip (Pyodide {PYODIDE_VERSION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
