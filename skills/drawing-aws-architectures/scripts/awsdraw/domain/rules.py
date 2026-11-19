"""Validation of an Architecture. Pure functions returning Findings (codes AWS001-AWS008)."""

from __future__ import annotations

from . import catalog
from .models import TIERS, Architecture, Finding

MAX_COMPONENTS = 20
SOFT_LIMIT = 16


def validate(arch: Architecture) -> list[Finding]:
    out: list[Finding] = []
    err = lambda c, m: out.append(Finding(c, "error", m))  # noqa: E731
    warn = lambda c, m: out.append(Finding(c, "warning", m))  # noqa: E731

    ids: set[str] = set()
    for comp in arch.components:
        if comp.id in ids:
            err("AWS001", f"Duplicate component id '{comp.id}'; ids must be unique.")
        ids.add(comp.id)
        if catalog.lookup(comp.service) is None:
            hint = catalog.suggestions(comp.service)
            more = f" Did you mean: {', '.join(hint)}?" if hint else " Run 'catalog' to list valid services."
            err("AWS002", f"Component '{comp.id}': unknown service '{comp.service}'.{more}")
        if comp.tier is not None and comp.tier not in TIERS:
            err("AWS007", f"Component '{comp.id}': tier '{comp.tier}' must be one of {', '.join(TIERS)}.")
    if not arch.components:
        err("AWS004", "The architecture has no components.")

    touched: set[str] = set()
    for f in arch.flows:
        for end in (f.source, f.target):
            if end not in ids:
                err("AWS003", f"Flow {f.source}->{f.target} references unknown component '{end}'.")
        if f.source == f.target:
            err("AWS008", f"Flow {f.source}->{f.target} connects a component to itself.")
        touched.update((f.source, f.target))

    if len(arch.components) > MAX_COMPONENTS:
        err("AWS005", f"{len(arch.components)} components is too many for a high-level view (max {MAX_COMPONENTS}); group related services.")
    elif len(arch.components) > SOFT_LIMIT:
        warn("AWS005", f"{len(arch.components)} components; high-level diagrams read best with {SOFT_LIMIT} or fewer.")

    for comp in arch.components:
        svc = catalog.lookup(comp.service)
        tier = comp.tier or (svc.tier if svc else None)
        if comp.id not in touched and tier != "ops" and len(arch.components) > 1:
            warn("AWS006", f"Component '{comp.id}' has no flows; connect it or remove it.")
    return out


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == "error" for f in findings)
