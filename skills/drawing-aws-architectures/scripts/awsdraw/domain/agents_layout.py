"""Fixed layout for the agent profile (zones, items and conceptual arrows). Pure."""

from __future__ import annotations

from dataclasses import dataclass

from . import system_design
from .agents import AgentView
from .layout import Rect


@dataclass(frozen=True)
class Zone:
    id: str
    title: str
    rect: Rect
    fill: str
    stroke: str


@dataclass(frozen=True)
class Item:
    id: str
    label: str
    note: str
    rect: Rect
    fill: str
    stroke: str
    dashed: bool = False


@dataclass(frozen=True)
class Arrow:
    id: str
    source: str  # zone or item id
    target: str
    label: str
    exit: tuple[float, float]
    entry: tuple[float, float]
    both: bool = False
    dashed: bool = False


@dataclass(frozen=True)
class AgentsLayout:
    zones: tuple[Zone, ...]
    items: tuple[Item, ...]
    arrows: tuple[Arrow, ...]
    width: float
    height: float


IW, IH, GAP = 150, 46, 10  # item size and spacing
CENTER_X, CENTER_W = 270, 390
RIGHT_X, RIGHT_W = 730, 340


def _stack(zone_rect: Rect, comps, prefix, fill, stroke, top=36, placeholder=None) -> list[Item]:
    items = []
    for i, c in enumerate(comps):
        kind = system_design.kind_of(c)
        items.append(Item(f"{prefix}_{c.id}", system_design.generic_label(c), "", Rect(zone_rect.x + (zone_rect.w - IW) / 2, zone_rect.y + top + i * (IH + GAP), IW, IH), kind.fill, kind.stroke))
    if not comps and placeholder:
        items.append(Item(f"{prefix}_none", placeholder, "", Rect(zone_rect.x + (zone_rect.w - IW) / 2, zone_rect.y + top, IW, IH), "#FFFFFF", "#9AA5AE", True))
    return items


def _height(n: int, top=36, bottom=14) -> float:
    return top + max(n, 1) * (IH + GAP) - GAP + bottom


def compute(view: AgentView) -> AgentsLayout:
    z = view.zones
    zones: list[Zone] = []
    items: list[Item] = []

    # users + frontend (top, centre)
    users = Item("users_box", "Usuarios", "", Rect(CENTER_X + (CENTER_W - 170) / 2, 30, 170, 60), "#FFFFFF", "#232F3D")
    items.append(users)
    fe = list(z["frontend"])
    per_row = 3
    fe_rows = max(1, -(-len(fe) // per_row))
    fe_h = 40 + fe_rows * (IH + GAP) + 4
    fe_rect = Rect(CENTER_X, 150, CENTER_W, fe_h)
    zones.append(Zone("z_frontend", "Aplicación frontend", fe_rect, "#FFFFFF", "#232F3D"))
    for i, c in enumerate(fe or [None]):
        r, col = divmod(i, per_row)
        n_in_row = min(per_row, len(fe) - r * per_row) if fe else 1
        x0 = fe_rect.x + (fe_rect.w - (n_in_row * 118 + (n_in_row - 1) * 8)) / 2
        rect = Rect(x0 + col * 126, fe_rect.y + 34 + r * (IH + GAP), 118, IH)
        if c is None:
            items.append(Item("fe_none", "Interfaz de usuario", "", rect, "#FFFFFF", "#9AA5AE", True))
        else:
            kind = system_design.kind_of(c)
            items.append(Item(f"fe_{c.id}", system_design.generic_label(c), "", rect, kind.fill, kind.stroke))

    # agent runtime
    ag = list(z["agent"])
    ag_y = fe_rect.y + fe_h + 70
    ag_h = 40 + max(len(ag), 1) * (66 + GAP) - GAP + 16
    mem_est = max(_height(len(z['memory_short']), 64), _height(len(z['memory_long']), 64)) + 6
    ag_h = max(ag_h, mem_est + 24 + 46 + 12)
    ag_rect = Rect(CENTER_X, ag_y, CENTER_W, ag_h)
    zones.append(Zone("z_agent", "Entorno de ejecución del agente", ag_rect, "#DDF5E9", "#2E9E6B"))
    for i, c in enumerate(ag or [None]):
        rect = Rect(ag_rect.x + 30, ag_rect.y + 40 + i * (66 + GAP), ag_rect.w - 60, 66)
        label = system_design.generic_label(c) if c else "Agente"
        items.append(Item(f"ag_{c.id if c else 'none'}", label if c else "Agente", "Orquesta, razona y decide", rect, "#FFFFFF", "#2E9E6B", c is None))

    # model runtime
    md = list(z["model"])
    md_rect = Rect(CENTER_X, ag_rect.y + ag_h + 90, CENTER_W, _height(len(md)))
    zones.append(Zone("z_model", "Entorno de ejecución del modelo", md_rect, "#FFF3CF", "#D9A400"))
    items += _stack(md_rect, md, "md", "", "", placeholder="Modelo de IA")

    # memory (right of agent)
    half = (RIGHT_W - 30) / 2
    ms, ml = list(z["memory_short"]), list(z["memory_long"])
    mem_h = max(_height(len(ms), 64), _height(len(ml), 64)) + 6
    mem_rect = Rect(RIGHT_X, ag_rect.y, RIGHT_W, mem_h)
    zones.append(Zone("z_memory", "Memoria", mem_rect, "#FCE4E4", "#D9534F"))
    for idx, (title, comps, key) in enumerate((("Corto plazo", ms, "ms"), ("Largo plazo", ml, "ml"))):
        sub = Rect(mem_rect.x + 10 + idx * (half + 10), mem_rect.y + 34, half, mem_rect.h - 44)
        zones.append(Zone(f"z_{key}", title, sub, "#FFFFFF", "#D9534F"))
        for it in _stack(sub, comps, key, "", "", top=34, placeholder="Sin definir"):
            items.append(Item(it.id, it.label, it.note, Rect(sub.x + (sub.w - 124) / 2, it.rect.y, 124, IH), it.fill, it.stroke, it.dashed))

    # tools (right, level of the model)
    cells = (("Bases de datos", "tool_database", "td"), ("APIs", "tool_api", "ta"), ("Servicios", "tool_service", "ts"), ("Archivos", "tool_files", "tf"))
    cell_w = (RIGHT_W - 30) / 2
    row_h = [max(_height(len(z[cells[r * 2][1]]), 34), _height(len(z[cells[r * 2 + 1][1]]), 34)) for r in range(2)]
    pill_y = mem_rect.y + mem_rect.h + 24
    tools_y = pill_y + 46 + 28
    tools_rect = Rect(RIGHT_X, tools_y, RIGHT_W, 40 + sum(row_h) + 10 + 10)
    zones.append(Zone("z_tools", "Herramientas", tools_rect, "#DCE9FB", "#3B7DDD"))
    y = tools_rect.y + 36
    for r in range(2):
        for c in range(2):
            title, role, key = cells[r * 2 + c]
            sub = Rect(tools_rect.x + 10 + c * (cell_w + 10), y, cell_w, row_h[r])
            zones.append(Zone(f"z_{key}", title, sub, "#FFFFFF", "#3B7DDD"))
            for it in _stack(sub, list(z[role]), key, "", "", top=32, placeholder=None):
                items.append(Item(it.id, it.label, it.note, Rect(sub.x + (sub.w - 124) / 2, it.rect.y, 124, IH), it.fill, it.stroke, it.dashed))
        y += row_h[r] + 10

    # protocol pill + developers
    pill = Item("pill_protocol", "Protocolo (p. ej. MCP)", "", Rect(RIGHT_X + (RIGHT_W - 250) / 2, pill_y, 250, 46), "#FFFFFF", "#232F3D")
    items.append(pill)
    dev = Item("dev_box", "Equipo de desarrollo", "Construye, prueba y evalúa el agente", Rect(30, ag_rect.y + 20, 190, 70), "#FFFFFF", "#232F3D")
    items.append(dev)

    # support band
    sup = list(z["support"])
    bottom = max(md_rect.y + md_rect.h, tools_rect.y + tools_rect.h) + 40
    if sup:
        bar = Rect(30, bottom, RIGHT_X + RIGHT_W - 30, 30)
        zones.append(Zone("z_support", "Siempre activos: seguridad, guardrails, observabilidad y evaluación", bar, "#FFFFFF", "#FFFFFF"))
        for i, c in enumerate(sup):
            items.append(Item(f"sp_{c.id}", system_design.generic_label(c), "", Rect(30 + i * 190, bottom + 34, 176, IH), "#F2F3F3", "#879196", True))
        bottom += 34 + IH
    width, height = RIGHT_X + RIGHT_W + 30, bottom + 40

    arrows = (
        Arrow("a_users_fe", "users_box", "z_frontend", "", (0.5, 1), (0.5, 0), both=True),
        Arrow("a_fe_agent", "z_frontend", "z_agent", "", (0.5, 1), (0.5, 0), both=True),
        Arrow("a_agent_mem", "z_agent", "z_memory", "", (1, 0.25), (0, 0.5), both=True),
        Arrow("a_agent_model", "z_agent", "z_model", "Solicitud de inferencia", (0.25, 1), (0.25, 0)),
        Arrow("a_model_agent", "z_model", "z_agent", "Respuesta", (0.75, 0), (0.75, 1)),
        Arrow("a_agent_pill", "z_agent", "pill_protocol", "", (1, (pill_y + 23 - ag_rect.y) / ag_rect.h), (0, 0.5), both=True),
        Arrow("a_pill_tools", "pill_protocol", "z_tools", "", (0.5, 1), (0.5, 0), both=True),
        Arrow("a_dev_agent", "dev_box", "z_agent", "", (1, 0.5), (0, 0.4), dashed=True),
    )
    return AgentsLayout(tuple(zones), tuple(items), arrows, width, height)
