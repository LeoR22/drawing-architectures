"""Composition root + command line: the only place that wires adapters to use cases."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .adapters import json_spec, readers, svg_preview
from .adapters.drawio_renderer import DrawioRenderer
from .adapters.fs_installer import EXTENSION_ID, FsInstaller
from .adapters.fs_writer import FsWriter
from .adapters.llm_anthropic import AnthropicPlanner
from .adapters.llm_github import GithubModelsPlanner
from .adapters.vscode_opener import VsCodeOpener
from .application.use_cases import CollectRequirements, GenerateDiagram, PlanAndGenerate, SaveDiagram
from .domain import catalog
from .domain.errors import SpecError
from .domain.models import Requirements
from .domain.planner import RulePlanner

SKILL_ROOT = Path(__file__).resolve().parents[2]
SKILL_NAME = "drawing-aws-architectures"


def _report(result, path: str, opened: bool, started: float) -> None:
    arch = result.architecture
    print(f"Wrote {path}  ({len(arch.components)} components, {len(arch.flows)} flows, {time.perf_counter() - started:.2f}s)")
    for f in result.findings:
        print(f"  {f.severity.upper()} {f.code}: {f.message}")
    print("Opened in VS Code." if opened else f"Open it in VS Code (extension {EXTENSION_ID}): code \"{path}\"")


def cmd_generate(args) -> int:
    started = time.perf_counter()
    generate = GenerateDiagram(DrawioRenderer())
    result = generate(json_spec.load(args.spec))
    out = args.output or str(Path(args.spec).with_suffix(".drawio"))
    saved, opened = SaveDiagram(FsWriter(), VsCodeOpener())(result, out, args.open)
    _report(result, saved, opened, started)
    return 0


def cmd_validate(args) -> int:
    from .domain.rules import has_errors, validate

    findings = validate(json_spec.load(args.spec))
    for f in findings:
        print(f"{f.severity.upper()} {f.code}: {f.message}")
    print("OK" if not has_errors(findings) else "FAILED")
    return 1 if has_errors(findings) else 0


def cmd_plan(args) -> int:
    """Offline: requirements file/text -> spec JSON (and optionally the diagram)."""
    started = time.perf_counter()
    collect = CollectRequirements(readers.read_document)
    req, warnings = collect(args.text or "", args.files or [])
    for w in warnings:
        print(f"WARNING {w}", file=sys.stderr)
    generate = GenerateDiagram(DrawioRenderer())
    result = PlanAndGenerate(RulePlanner(), generate)(req)
    out = args.output or "architecture.drawio"
    saved, opened = SaveDiagram(FsWriter(), VsCodeOpener())(result, out, args.open)
    _report(result, saved, opened, started)
    return 0


def cmd_catalog(_args) -> int:
    for tier in ("actors", "edge", "app", "data", "ops"):
        keys = [s.key for s in catalog.SERVICES.values() if s.tier == tier]
        print(f"{tier:7} {', '.join(keys)}")
    print("aliases:", ", ".join(sorted(catalog.ALIASES)))
    return 0


def cmd_install(args) -> int:
    dest = FsInstaller().install(SKILL_ROOT, SKILL_NAME, args.scope, args.target, args.project)
    print(f"Installed to {dest}")
    print(f"VS Code: install the extension '{EXTENSION_ID}' (Draw.io Integration) to view .drawio files.")
    return 0


def cmd_ui(args) -> int:
    from .adapters import web_ui

    rule = RulePlanner()
    providers = {"github": GithubModelsPlanner, "anthropic": AnthropicPlanner}
    enabled = [k for k, cls in providers.items() if cls.available()]
    generate = GenerateDiagram(DrawioRenderer())
    collect = CollectRequirements(readers.read_document)
    out_dir = Path(args.output_dir).resolve()
    opener, writer = VsCodeOpener(), FsWriter()

    def analyze(text: str, paths: list[str], mode: str) -> dict:
        started = time.perf_counter()
        req, warnings = collect(text, paths)
        used = "offline"
        if mode in enabled:
            result = PlanAndGenerate(providers[mode](), generate, fallback=rule)(req)
            used = mode
        else:
            if mode in providers:
                warnings.append(f"Mode '{mode}' is not configured (see reference/ui.md); used offline rules instead.")
            if req.images and not req.text.strip():
                raise SpecError("Images need an AI mode: set GITHUB_MODELS_TOKEN or ANTHROPIC_API_KEY, or describe the images in text.")
            if req.images:
                warnings.append("Offline mode ignores images; only the text was used.")
            result = PlanAndGenerate(rule, generate)(Requirements(req.text))
        name = "".join(ch if ch.isalnum() else "-" for ch in result.architecture.title.lower()).strip("-")[:40] or "architecture"
        return {
            "title": result.architecture.title, "planner": used, "filename": f"{name}.drawio",
            "xml": result.xml, "svg": svg_preview.render(result.architecture, result.layout),
            "components": [{"id": c.id, "service": c.service, "label": c.label} for c in result.architecture.components],
            "warnings": warnings + [f"{f.code}: {f.message}" for f in result.findings],
            "seconds": round(time.perf_counter() - started, 2),
        }

    def save(xml: str, filename: str) -> tuple[str, bool]:
        if not xml.startswith("<?xml") or "<mxfile" not in xml[:400] or len(xml) > 5_000_000:
            raise SpecError("Nothing valid to save; generate the diagram first.")
        safe = web_ui._safe_name(filename, "architecture.drawio")
        if not safe.lower().endswith(".drawio"):
            safe += ".drawio"
        saved = writer.write(str(out_dir / safe), xml)
        return saved, opener.open(saved)

    page = (Path(__file__).parent / "adapters" / "ui_page.html").read_text(encoding="utf-8")
    server = web_ui.serve(web_ui.UiDeps(analyze, save, enabled), page, args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"UI running at {url}  (Ctrl+C to stop). Diagrams are saved to {out_dir}")
    if args.browser:
        import webbrowser

        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="awsdraw", description="High-level AWS architecture -> draw.io (VS Code).")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="spec JSON -> .drawio")
    g.add_argument("spec"); g.add_argument("-o", "--output"); g.add_argument("--open", action="store_true", help="open in VS Code")
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("validate", help="check a spec without writing anything")
    v.add_argument("spec"); v.set_defaults(func=cmd_validate)

    pl = sub.add_parser("plan", help="offline: requirements text/files -> .drawio in one step")
    pl.add_argument("text", nargs="?", default=""); pl.add_argument("-f", "--files", nargs="*")
    pl.add_argument("-o", "--output"); pl.add_argument("--open", action="store_true")
    pl.set_defaults(func=cmd_plan)

    c = sub.add_parser("catalog", help="list supported AWS services"); c.set_defaults(func=cmd_catalog)

    i = sub.add_parser("install", help="install this skill for VS Code")
    i.add_argument("--scope", choices=("project", "user"), default="project")
    i.add_argument("--target", choices=("copilot", "claude", "agents"), default="copilot")
    i.add_argument("--project", help="project folder (default: current directory)")
    i.set_defaults(func=cmd_install)

    u = sub.add_parser("ui", help="start the local web interface")
    u.add_argument("--port", type=int, default=8765); u.add_argument("--output-dir", default="diagrams")
    u.add_argument("--browser", action="store_true", help="open the page in the default browser")
    u.set_defaults(func=cmd_ui)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
