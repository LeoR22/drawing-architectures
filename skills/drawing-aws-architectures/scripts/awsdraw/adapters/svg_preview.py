"""Lightweight SVG preview of a Layout for the local UI (no draw.io needed; coloured tiles, not real AWS icons)."""

from __future__ import annotations

from xml.sax.saxutils import escape

from ..domain.layout import Layout
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
