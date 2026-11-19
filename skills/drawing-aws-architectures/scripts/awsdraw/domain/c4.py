"""C4 model views (levels 1 and 2) derived from the architecture. Pure.

Level 1 - System context: people, the system as one box, and external systems it depends on.
Level 2 - Containers: the deployable/runnable building blocks inside the system boundary.
C4 shows technology per container, so the service name appears as "[Tecnología: X]" there.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import catalog, system_design
from .layout import Layout, Rect, skips_over
from .models import Architecture

PERSON, SYSTEM, CONTAINER, EXTERNAL, DATABASE = "person", "system", "container", "external", "database"
COLORS = {PERSON: ("#08427B", "#073B6F"), SYSTEM: ("#1168BD", "#0B4884"), CONTAINER: ("#438DD5", "#3C7FC0"),
          DATABASE: ("#438DD5", "#3C7FC0"), EXTERNAL: ("#8A8A8A", "#6B6B6B")}
BW, BH, STEP_X = 190, 110, 250
_PEOPLE = {"actor", "client", "mobile"}
_EXTERNAL = {"auth": "Proveedor de identidad", "pubsub": "Servicio de notificaciones"}
_DATA = {"db", "warehouse", "object", "cache", "search"}
_SKIP = {"observability", "audit", "secrets", "security", "backup", "iac", "firewall"}


@dataclass(frozen=True)
class Box:
    id: str
    type: str
    name: str
    tech: str
    desc: str
    rect: Rect


@dataclass(frozen=True)
class Rel:
    source: str
    target: str
    label: str
    mode: str  # "right" | "down" | "up" | "left" | "over"
    async_: bool = False


@dataclass(frozen=True)
class View:
    title: str
    boxes: tuple[Box, ...]
    rels: tuple[Rel, ...]
    boundary: tuple[str, Rect] | None
    width: float
    height: float


def _short(text: str, n: int = 40) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _kind_key(component) -> str:
    return system_design.kind_of(component).key


def context(arch: Architecture) -> View:
    people = [c for c in arch.components if _kind_key(c) in _PEOPLE]
    ext = [c for c in arch.components if _kind_key(c) in _EXTERNAL]
    n = max(len(people), len(ext), 1)
    width = n * 270 + 120
    cx = width / 2

    def row(count, y, w=BW):
        x0 = cx - (count * (w + 70) - 70) / 2
        return [Rect(x0 + i * (w + 70), y, w, BH) for i in range(count)]

    boxes, rels = [], []
    for c, r in zip(people, row(len(people), 90)):
        boxes.append(Box(f"p_{c.id}", PERSON, system_design.generic_label(c), "", "Persona que usa la solución", r))
    sys_rect = Rect(cx - 150, 330, 300, 140)
    boxes.append(Box("system", SYSTEM, _short(arch.title), "", "La solución que se diseña", sys_rect))
    for c, r in zip(ext, row(len(ext), 600)):
        boxes.append(Box(f"x_{c.id}", EXTERNAL, _EXTERNAL[_kind_key(c)], "", "Sistema externo del que depende", r))
    for c in people:
        rels.append(Rel(f"p_{c.id}", "system", "Usa", "down"))
    for c in ext:
        rels.append(Rel("system", f"x_{c.id}", "Usa", "down", True))
    return View(f"C4 · Nivel 1 · Contexto: {_short(arch.title)}", tuple(boxes), tuple(rels), None, width, 600 + BH + 60 if ext else 520 + 60)


def containers(arch: Architecture, layout: Layout) -> View:
    keep = [n for n in layout.nodes if _kind_key(n.component) not in _SKIP and _kind_key(n.component) not in _EXTERNAL]
    if not keep:
        return View("C4 · Nivel 2 · Contenedores", (), (), None, 400, 300)
    ids = {n.component.id for n in keep}
    x0, y0 = min(n.rect.x for n in keep), min(n.rect.y for n in keep)
    boxes, by_col = [], {}
    for n in keep:
        key = _kind_key(n.component)
        kind = PERSON if key in _PEOPLE else DATABASE if key in _DATA else CONTAINER
        x, y = 60 + (n.column) * STEP_X, 120 + (n.rect.y - y0) * 1.0
        tech = catalog.lookup(n.component.service).label
        box = Box(n.component.id, kind, system_design.generic_label(n.component), tech if kind != PERSON else "",
                  system_design.kind_of(n.component).title if kind != PERSON else "Persona que usa la solución", Rect(x, y, BW, BH))
        boxes.append(box)
        by_col[n.component.id] = n.column
    inner = [b for b in boxes if b.type != PERSON]
    boundary = None
    if inner:
        bx, by = min(b.rect.x for b in inner) - 30, min(b.rect.y for b in inner) - 46
        bx2, by2 = max(b.rect.x + b.rect.w for b in inner) + 30, max(b.rect.y + b.rect.h for b in inner) + 30
        boundary = (_short(arch.title), Rect(bx, by, bx2 - bx, by2 - by))
    rels = []
    for f in arch.flows:
        if f.source not in ids or f.target not in ids:
            continue
        c1, c2 = by_col[f.source], by_col[f.target]
        y1 = next(b.rect.y for b in boxes if b.id == f.source)
        y2 = next(b.rect.y for b in boxes if b.id == f.target)
        if c2 > c1:
            mode = "over" if skips_over(layout.nodes, f.source, f.target) else "right"
        elif c2 == c1:
            mode = "down" if y2 > y1 else "up"
        else:
            mode = "left"
        rels.append(Rel(f.source, f.target, f.label, mode, f.is_async))
    width = max(b.rect.x + b.rect.w for b in boxes) + 60
    height = max(b.rect.y + b.rect.h for b in boxes) + 80
    return View(f"C4 · Nivel 2 · Contenedores: {_short(arch.title)}", tuple(boxes), tuple(rels), boundary, width, height)
