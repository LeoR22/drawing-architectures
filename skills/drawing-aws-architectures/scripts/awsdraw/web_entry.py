"""Entry points for the in-browser engine (Pyodide). Every function takes/returns JSON strings.

Network calls to AI providers happen in the page's JavaScript (Pyodide has no sockets); this module
supplies the prompt, parses the model reply and does all deterministic work (validate, layout, draw).
"""

from __future__ import annotations

import json
import time

from .adapters import readers
from .adapters.drawio_renderer import DrawioRenderer
from .adapters.llm_common import parse_reply, system_prompt
from .adapters.ui_response import to_response
from .application.use_cases import CollectRequirements, GenerateDiagram, PlanAndGenerate
from .domain.errors import SpecError
from .domain.models import Requirements
from .domain.planner import RulePlanner

_generate = GenerateDiagram(DrawioRenderer())


def _safe(fn):
    def wrapper(*args):
        try:
            return json.dumps(fn(*args))
        except SpecError as exc:
            return json.dumps({"error": str(exc)})
    return wrapper


@_safe
def collect(text: str, paths_json: str) -> dict:
    req, warnings = CollectRequirements(readers.read_document)(text, json.loads(paths_json))
    return {"text": req.text, "warnings": warnings}


@_safe
def plan_offline(text: str, warnings_json: str) -> dict:
    started = time.perf_counter()
    result = PlanAndGenerate(RulePlanner(), _generate)(Requirements(text))
    return to_response(result, "offline", json.loads(warnings_json), started)


def ai_system_prompt() -> str:
    return system_prompt()


@_safe
def finish_ai(reply: str, text: str, provider: str, warnings_json: str) -> dict:
    """Turn the model's raw reply into a diagram; fall back to offline rules if it is unusable."""
    started = time.perf_counter()
    warnings = json.loads(warnings_json)
    try:
        result = _generate(parse_reply(reply))
        return to_response(result, provider, warnings, started)
    except SpecError as exc:
        if not text.strip():
            raise
        result = PlanAndGenerate(RulePlanner(), _generate)(Requirements(text))
        return to_response(result, "offline", warnings + [f"The AI reply was unusable ({exc}); offline rules were used."], started)
