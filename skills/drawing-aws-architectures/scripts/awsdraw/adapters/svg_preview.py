"""Lightweight SVG preview of a Layout for the local UI (no draw.io needed; coloured tiles, not real AWS icons)."""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..domain.layout import Layout, skips_over
from ..domain.models import Architecture

_GROUP = {"cloud": ("#232F3E", ""), "region": ("#00A4A6", "6 4"), "vpc": ("#8C4FFF", "")}


def render(arch: Architecture, layout: Layout) -> str:
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {layout.width:g} {layout.height:g}" font-family="Arial,sans-serif">',
        '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#232F3E"/></marker></defs>',
        f'<text x="{layout.title_at[0]:g}" y="{layout.title_at[1] + 22:g}" font-size="20" font-weight="bold" fill="#232F3E">{escape(arch.title)}</text>',
    ]
    for g in layout.groups:
        color, dash = _GROUP[g.kind]
        d = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<rect x="{g.rect.x:g}" y="{g.rect.y:g}" width="{g.rect.w:g}" height="{g.rect.h:g}" fill="none" stroke="{color}"{d}/>')
        out.append(f'<text x="{g.rect.x + 8:g}" y="{g.rect.y + 18:g}" font-size="13" fill="{color}">{escape(g.label)}</text>')
    pos = {n.component.id: n.rect for n in layout.nodes}
    for f in arch.flows:
        a, b = pos[f.source], pos[f.target]
        ax, ay, bx, by = a.x + 39, a.y + 39, b.x + 39, b.y + 39
        if b.x > a.x:
            ax, bx = a.x + 78, b.x
        elif b.x == a.x:  # same column: leave from the icon edge, not through the label
            ay, by = (a.y + 78, b.y) if b.y > a.y else (a.y, b.y + 78)
        dash = ' stroke-dasharray="6 4"' if f.is_async else ""
        out.append(f'<line x1="{ax:g}" y1="{ay:g}" x2="{bx:g}" y2="{by:g}" stroke="#232F3E" stroke-width="2"{dash} marker-end="url(#a)"/>')
    for n in layout.nodes:
        r = n.rect
        out.append(f'<rect x="{r.x:g}" y="{r.y:g}" width="78" height="78" rx="6" fill="{n.service.color}"/>')
        out.append(f'<text x="{r.x + 39:g}" y="{r.y + 45:g}" text-anchor="middle" font-size="12" fill="#fff" font-weight="bold">{escape(n.service.key[:9])}</text>')
        label = n.component.label or n.service.label
        out.append(f'<text x="{r.x + 39:g}" y="{r.y + 96:g}" text-anchor="middle" font-size="12" fill="#232F3E">{escape(label[:26])}</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---- level 1 preview -------------------------------------------------------------------------
import textwrap  # noqa: E402

from ..domain.overview import Overview  # noqa: E402
from ..domain.overview_layout import OverviewLayout  # noqa: E402

_COLORS = {0: ("#232F3D", "#232F3D", "#FFFFFF"), 1: ("#EFE8FF", "#8C4FFF", "#232F3E"), 2: ("#FFF1E0", "#ED7100", "#232F3E"), 3: ("#F7E6FA", "#C925D1", "#232F3E")}


def _lines(x: float, y: float, rows: list[tuple[str, int, str, bool]]) -> str:
    out = []
    for text, size, color, bold in rows:
        weight = ' font-weight="bold"' if bold else ""
        out.append(f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color}"{weight}>{escape(text)}</text>')
        y += size + 5
    return "".join(out)


def render_overview(ov: Overview, lay: OverviewLayout) -> str:
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lay.width:g} {lay.height:g}" font-family="Arial,sans-serif">',
        '<defs><marker id="b" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#232F3E"/></marker></defs>',
        f'<text x="{lay.title_at[0]:g}" y="{lay.title_at[1] + 22:g}" font-size="20" font-weight="bold" fill="#232F3E">{escape(ov.title[:70])}</text>',
    ]
    cols = {b.key: b.column for b in ov.boxes}
    order = {k: i for i, k in enumerate(sorted(set(cols.values())))}
    for link in ov.links:
        a, b = lay.boxes[link.source], lay.boxes[link.target]
        if order[cols[link.target]] - order[cols[link.source]] > 1:  # skips a column: arch over the top
            x1, x2, top = a.x + a.w / 2, b.x + b.w / 2, min(a.y, b.y) - 34
            out.append(f'<path d="M{x1:g},{a.y:g} V{top:g} H{x2:g} V{b.y:g}" fill="none" stroke="#232F3E" stroke-width="2" marker-end="url(#b)"/>')
            out.append(f'<circle cx="{(x1 + x2) / 2:g}" cy="{top:g}" r="12" fill="#ED7100"/><text x="{(x1 + x2) / 2:g}" y="{top + 5:g}" text-anchor="middle" font-size="13" font-weight="bold" fill="#fff">{link.step}</text>')
            continue
        if cols[link.target] > cols[link.source]:
            x1, y1, x2, y2 = a.x + a.w, a.y + a.h / 2, b.x, b.y + b.h / 2
        else:
            x1, y1, x2, y2 = (a.x + a.w / 2, a.y + a.h, b.x + b.w / 2, b.y) if b.y > a.y else (a.x + a.w / 2, a.y, b.x + b.w / 2, b.y + b.h)
        out.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="#232F3E" stroke-width="2" marker-end="url(#b)"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append(f'<circle cx="{mx:g}" cy="{my:g}" r="12" fill="#ED7100"/><text x="{mx:g}" y="{my + 5:g}" text-anchor="middle" font-size="13" font-weight="bold" fill="#fff">{link.step}</text>')
    for box in ov.boxes:
        fill, stroke, font = _COLORS[box.column]
        r = lay.boxes[box.key]
        rows = [(box.title, 15, font, True)] + [(t, 11, font, False) for t in textwrap.wrap(box.does, 38)]
        if box.key != "people":
            rows += [(f"• {i}", 12, font, False) for i in box.items]
            rows += [(t, 10, "#687078", False) for t in textwrap.wrap("AWS: " + ", ".join(box.services), 46)]
        out.append(f'<rect x="{r.x:g}" y="{r.y:g}" width="{r.w:g}" height="{r.h:g}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        out.append(_lines(r.x + 12, r.y + 22, rows))
    if ov.support and lay.band_label:
        out.append(f'<text x="{lay.band_label.x:g}" y="{lay.band_label.y + 18:g}" font-size="13" font-weight="bold" fill="#232F3E">Siempre activos: seguridad y operación</text>')
        for b in ov.support:
            r = lay.chips[b.key]
            out.append(f'<rect x="{r.x:g}" y="{r.y:g}" width="{r.w:g}" height="{r.h:g}" rx="8" fill="#F2F3F3" stroke="#879196" stroke-dasharray="5 3"/>')
            out.append(_lines(r.x + 10, r.y + 18, [(b.title, 12, "#232F3E", True)] + [(t, 10, "#687078", False) for t in textwrap.wrap(", ".join(b.services), 40)[:1]]))
    s = lay.story
    out.append(f'<rect x="{s.x:g}" y="{s.y:g}" width="{s.w:g}" height="{s.h:g}" fill="#FAFAFA" stroke="#D5DBDB"/>')
    rows = [("Cómo explicarlo, paso a paso", 13, "#232F3E", True)] + [(t, 12, "#232F3E", False) for line in ov.story for t in textwrap.wrap(line, 175)]
    out.append(_lines(s.x + 10, s.y + 22, rows))
    out.append("</svg>")
    return "\n".join(out)


# ---- level 1 (system design) preview ---------------------------------------------------------
from ..domain import system_design  # noqa: E402

_SIZES = {"actor": (40, 70), "hexagon": (130, 64), "cloud": (130, 76), "service": (130, 64), "cylinder": (100, 78), "process": (130, 64), "model": (130, 64), "support": (130, 64)}


def _shape(kind, cx: float, cy: float) -> str:
    w, h = _SIZES[kind.shape]
    x, y = cx - w / 2, cy - h / 2
    st = f'fill="{kind.fill}" stroke="{kind.stroke}" stroke-width="2"'
    if kind.shape == "actor":
        return (f'<circle cx="{cx:g}" cy="{y + 10:g}" r="9" {st}/><path d="M{cx:g},{y + 19:g} V{y + 46:g} M{cx - 16:g},{y + 29:g} H{cx + 16:g} '
                f'M{cx:g},{y + 46:g} L{cx - 14:g},{y + 68:g} M{cx:g},{y + 46:g} L{cx + 14:g},{y + 68:g}" fill="none" stroke="{kind.stroke}" stroke-width="2"/>')
    if kind.shape == "hexagon":
        pts = f"{x + 18:g},{y:g} {x + w - 18:g},{y:g} {x + w:g},{cy:g} {x + w - 18:g},{y + h:g} {x + 18:g},{y + h:g} {x:g},{cy:g}"
        return f'<polygon points="{pts}" {st}/>'
    if kind.shape == "cloud":
        return f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{w / 2:g}" ry="{h / 2:g}" {st}/>'
    if kind.shape == "cylinder":
        return (f'<path d="M{x:g},{y + 12:g} V{y + h - 12:g} A{w / 2:g},12 0 0 0 {x + w:g},{y + h - 12:g} V{y + 12:g}" {st}/>'
                f'<ellipse cx="{cx:g}" cy="{y + 12:g}" rx="{w / 2:g}" ry="12" {st}/>')
    dash = ' stroke-dasharray="5 3"' if kind.shape == "support" else ""
    rect = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{14 if kind.shape == "model" else 8}" {st}{dash}/>'
    if kind.shape == "process":
        rect += f'<path d="M{x + 12:g},{y:g} V{y + h:g} M{x + w - 12:g},{y:g} V{y + h:g}" stroke="{kind.stroke}" stroke-width="2"/>'
    return rect


def render_system_design(arch: Architecture, layout: Layout) -> str:
    xs, ys = [n.rect.x for n in layout.nodes], [n.rect.y for n in layout.nodes]
    dx, dy = 40 - min(xs), 110 - min(ys)
    width, height = max(xs) + 78 + dx + 100, max(ys) + 108 + dy + 40
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" font-family="Arial,sans-serif">',
        '<defs><marker id="c" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#232F3E"/></marker></defs>',
        f'<text x="40" y="42" font-size="20" font-weight="bold" fill="#232F3E">{escape(arch.title[:70])}</text>',
        '<text x="40" y="66" font-size="13" fill="#687078">Bloques genéricos, sin nombres de servicios: sirve para cualquier nube.</text>',
    ]
    pos = {}
    for n in layout.nodes:
        pos[n.component.id] = (n.rect.x + dx + 39, n.rect.y + dy + 39, system_design.kind_of(n.component))
    for f in arch.flows:
        (ax, ay, ka), (bx, by, kb) = pos[f.source], pos[f.target]
        wa, ha = _SIZES[ka.shape]
        wb, hb = _SIZES[kb.shape]
        if skips_over(layout.nodes, f.source, f.target):
            top = min(ay - ha / 2, by - hb / 2) - 30
            dash = ' stroke-dasharray="6 4"' if f.is_async else ""
            out.append(f'<path d="M{ax:g},{ay - ha / 2:g} V{top:g} H{bx:g} V{by - hb / 2:g}" fill="none" stroke="#232F3E" stroke-width="2"{dash} marker-end="url(#c)"/>')
            continue
        if bx > ax + 1:
            x1, y1, x2, y2 = ax + wa / 2, ay, bx - wb / 2, by
        elif abs(bx - ax) <= 1:
            x1, y1, x2, y2 = (ax, ay + ha / 2, bx, by - hb / 2) if by > ay else (ax, ay - ha / 2, bx, by + hb / 2)
        else:
            x1, y1, x2, y2 = ax - wa / 2, ay, bx + wb / 2, by
        dash = ' stroke-dasharray="6 4"' if f.is_async else ""
        out.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="#232F3E" stroke-width="2"{dash} marker-end="url(#c)"/>')
    for n in layout.nodes:
        cx, cy, kind = pos[n.component.id]
        out.append(_shape(kind, cx, cy))
        label = system_design.generic_label(n.component)
        lines = textwrap.wrap(label, 18)[:3]
        if kind.shape == "actor":
            ty = cy + 47
        else:
            ty = cy - (len(lines) - 1) * 7 + 4
        for i, line in enumerate(lines):
            out.append(f'<text x="{cx:g}" y="{ty + i * 14:g}" text-anchor="middle" font-size="12" fill="#232F3E">{escape(line)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def render_agents(arch: Architecture) -> str:
    from ..domain import agents, agents_layout

    lay = agents_layout.compute(agents.classify(arch))
    rects = {z.id: z.rect for z in lay.zones} | {i.id: i.rect for i in lay.items}
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lay.width:g} {lay.height:g}" font-family="Arial,sans-serif">',
        '<defs><marker id="c" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 z" fill="#232F3E"/></marker></defs>',
        f'<text x="30" y="26" font-size="18" font-weight="bold" fill="#232F3E">{escape(arch.title[:70])}</text>',
    ]
    for z in lay.zones:
        r = z.rect
        out.append(f'<rect x="{r.x:g}" y="{r.y:g}" width="{r.w:g}" height="{r.h:g}" rx="8" fill="{z.fill}" stroke="{z.stroke}" stroke-width="2"/>')
        out.append(f'<text x="{r.x + 10:g}" y="{r.y + 20:g}" font-size="12" font-weight="bold" fill="#232F3E">{escape(z.title)}</text>')
    for a in lay.arrows:
        s_, t_ = rects[a.source], rects[a.target]
        x1, y1 = s_.x + s_.w * a.exit[0], s_.y + s_.h * a.exit[1]
        x2, y2 = t_.x + t_.w * a.entry[0], t_.y + t_.h * a.entry[1]
        dash = ' stroke-dasharray="6 4"' if a.dashed else ""
        start = ' marker-start="url(#c)"' if a.both else ""
        out.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="#232F3E" stroke-width="2"{dash}{start} marker-end="url(#c)"/>')
        if a.label:
            out.append(f'<text x="{(x1 + x2) / 2 + 6:g}" y="{(y1 + y2) / 2:g}" font-size="11" fill="#687078">{escape(a.label)}</text>')
    for it in lay.items:
        r = it.rect
        dash = ' stroke-dasharray="5 3"' if it.dashed else ""
        out.append(f'<rect x="{r.x:g}" y="{r.y:g}" width="{r.w:g}" height="{r.h:g}" rx="8" fill="{it.fill or "#FFFFFF"}" stroke="{it.stroke or "#9AA5AE"}" stroke-width="2"{dash}/>')
        lines = textwrap.wrap(it.label, 22)[:2]
        base = r.y + (r.h / 2 - (len(lines) - 1) * 7 + 4 - (8 if it.note else 0))
        for i, line in enumerate(lines):
            out.append(f'<text x="{r.x + r.w / 2:g}" y="{base + i * 14:g}" text-anchor="middle" font-size="12" fill="#232F3E">{escape(line)}</text>')
        if it.note:
            out.append(f'<text x="{r.x + r.w / 2:g}" y="{r.y + r.h - 12:g}" text-anchor="middle" font-size="10" fill="#687078">{escape(it.note[:46])}</text>')
    out.append("</svg>")
    return "".join(out)


def render_c4(view) -> str:
    from ..domain import c4

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view.width:g} {view.height:g}" font-family="Arial,sans-serif">',
        '<defs><marker id="c" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#444"/></marker></defs>',
        f'<text x="30" y="30" font-size="17" font-weight="bold" fill="#232F3E">{escape(view.title[:80])}</text>',
    ]
    if view.boundary:
        t, r = view.boundary
        out.append(f'<rect x="{r.x:g}" y="{r.y:g}" width="{r.w:g}" height="{r.h:g}" rx="6" fill="none" stroke="#444" stroke-width="2" stroke-dasharray="8 6"/>')
        out.append(f'<text x="{r.x + 12:g}" y="{r.y + 20:g}" font-size="12" font-weight="bold" fill="#444">{escape(t[:50])}</text><text x="{r.x + 12:g}" y="{r.y + 34:g}" font-size="10" fill="#444">[Límite del sistema]</text>')
    rects = {b.id: b.rect for b in view.boxes}
    for rel in view.rels:
        a, b = rects[rel.source], rects[rel.target]
        dash = ' stroke-dasharray="6 4"' if rel.async_ else ""
        if rel.mode == "over":
            top = min(a.y, b.y) - 26
            d = f"M{a.x + a.w / 2:g},{a.y:g} V{top:g} H{b.x + b.w / 2:g} V{b.y:g}"
            lx, ly = (a.x + b.x + a.w) / 2, top - 4
        else:
            if rel.mode == "right":
                p1, p2 = (a.x + a.w, a.y + a.h / 2), (b.x, b.y + b.h / 2)
            elif rel.mode == "left":
                p1, p2 = (a.x, a.y + a.h / 2), (b.x + b.w, b.y + b.h / 2)
            elif rel.mode == "down":
                p1, p2 = (a.x + a.w / 2, a.y + a.h), (b.x + b.w / 2, b.y)
            else:
                p1, p2 = (a.x + a.w / 2, a.y), (b.x + b.w / 2, b.y + b.h)
            d = f"M{p1[0]:g},{p1[1]:g} L{p2[0]:g},{p2[1]:g}"
            lx, ly = (p1[0] + p2[0]) / 2 + 4, (p1[1] + p2[1]) / 2 - 4
        out.append(f'<path d="{d}" fill="none" stroke="#444" stroke-width="2"{dash} marker-end="url(#c)"/>')
        if rel.label:
            out.append(f'<text x="{lx:g}" y="{ly:g}" text-anchor="middle" font-size="11" fill="#444" stroke="#fff" stroke-width="4" paint-order="stroke">{escape(rel.label[:28])}</text>')
    kind = {c4.PERSON: "Persona", c4.SYSTEM: "Sistema de software", c4.EXTERNAL: "Sistema externo", c4.CONTAINER: "Contenedor", c4.DATABASE: "Contenedor"}
    for b in view.boxes:
        fill, stroke = c4.COLORS[b.type]
        r = b.rect
        out.append(f'<rect x="{r.x:g}" y="{r.y:g}" width="{r.w:g}" height="{r.h:g}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        lines = textwrap.wrap(b.name, 24)[:2]
        y = r.y + 26
        for ln in lines:
            out.append(f'<text x="{r.x + r.w / 2:g}" y="{y:g}" text-anchor="middle" font-size="13" font-weight="bold" fill="#fff">{escape(ln)}</text>')
            y += 16
        tag = f"[{kind[b.type]}" + (f", {b.tech}" if b.tech else "") + "]"
        out.append(f'<text x="{r.x + r.w / 2:g}" y="{y + 2:g}" text-anchor="middle" font-size="10" fill="#fff">{escape(tag[:34])}</text>')
        if b.desc:
            out.append(f'<text x="{r.x + r.w / 2:g}" y="{y + 20:g}" text-anchor="middle" font-size="10" fill="#E6EEF7">{escape(textwrap.shorten(b.desc, 34))}</text>')
    out.append("</svg>")
    return "".join(out)
