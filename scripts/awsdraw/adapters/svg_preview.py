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
