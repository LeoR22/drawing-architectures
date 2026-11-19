"""Parses the JSON spec format (see SKILL.md) into an Architecture."""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.errors import SpecError
from ..domain.models import Architecture, Component, Flow


def parse(data: object) -> Architecture:
    if not isinstance(data, dict):
        raise SpecError("The spec must be a JSON object with 'components' and 'flows'.")
    try:
        comps = tuple(
            Component(str(c["id"]), str(c["service"]), str(c.get("label") or ""), c.get("tier"), bool(c.get("vpc", False)))
            for c in data.get("components", [])
        )
        flows = tuple(
            Flow(str(f["from"]), str(f["to"]), str(f.get("label", "")), bool(f.get("async", False)))
            for f in data.get("flows", [])
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise SpecError(f"Malformed spec: each component needs 'id' and 'service'; each flow needs 'from' and 'to' ({exc}).") from None
    return Architecture(
        str(data.get("title") or "AWS high-level architecture"), comps, flows,
        str(data.get("region") or "us-east-1"), bool(data.get("multi_az", False)),
    )


def load(path: str) -> Architecture:
    p = Path(path)
    if not p.is_file():
        raise SpecError(f"Spec file not found: {path}")
    try:
        return parse(json.loads(p.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise SpecError(f"{p.name} is not valid JSON: {exc}.") from None
