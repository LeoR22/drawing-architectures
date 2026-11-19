"""Deterministic left-to-right layout. Pure: Architecture in, rectangles out.

Columns follow TIERS (actors | edge | app | data | ops). Components flagged `vpc`
are stacked below the non-VPC ones of their column so one VPC rectangle can wrap
them without touching anything else.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import catalog
from .models import TIERS, Architecture, Component

ICON, VISUAL_H = 78, 108  # icon box and icon+label height
COL_W, ROW_H = 190, 160
MARGIN = 30


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def union(self, o: "Rect") -> "Rect":
        x0, y0 = min(self.x, o.x), min(self.y, o.y)
        x1, y1 = max(self.x + self.w, o.x + o.w), max(self.y + self.h, o.y + o.h)
        return Rect(x0, y0, x1 - x0, y1 - y0)

    def pad(self, left: float, top: float, right: float, bottom: float) -> "Rect":
        return Rect(self.x - left, self.y - top, self.w + left + right, self.h + top + bottom)


@dataclass(frozen=True)
class Node:
    component: Component
    service: catalog.Service
    column: int
    row: int
    rect: Rect
    parent: str  # "1" (canvas) | "cloud" | "region" | "vpc"


@dataclass(frozen=True)
class Group:
    id: str
    kind: str  # cloud | region | vpc
    label: str
    rect: Rect
    parent: str


@dataclass(frozen=True)
class Layout:
    nodes: tuple[Node, ...]
    groups: tuple[Group, ...]
    width: float
    height: float
    title_at: tuple[float, float]


def _union_all(rects: list[Rect]) -> Rect:
    out = rects[0]
    for r in rects[1:]:
        out = out.union(r)
    return out


def _order_by_neighbours(columns: dict, arch: Architecture) -> None:
    """Barycentre ordering: a component sits near the average row of what feeds it, which cuts crossing arrows."""
    rank: dict[str, int] = {}
    for i in sorted(columns):
        def desired(entry):
            index, item = entry
            rows = [rank[f.source] for f in arch.flows if f.target == item[0].id and f.source in rank]
            return sum(rows) / len(rows) if rows else index
        ordered = [item for _, item in sorted(enumerate(columns[i]), key=lambda e: (desired(e), e[0]))]
        ids = {item[0].id for item in ordered}
        for f in arch.flows:  # a component fed from the same column goes right below its feeder
            if f.source in ids and f.target in ids and f.source != f.target:
                moving = next(it for it in ordered if it[0].id == f.target)
                ordered.remove(moving)
                at = next(n for n, it in enumerate(ordered) if it[0].id == f.source) + 1
                while at < len(ordered) and any(g.source == ordered[at - 1][0].id and g.target == ordered[at][0].id for g in arch.flows):
                    at += 1
                ordered.insert(at, moving)
        columns[i] = ordered
        rank.update({item[0].id: r for r, item in enumerate(ordered)})


def compute(arch: Architecture) -> Layout:
    resolved = []
    for c in arch.components:
        svc = catalog.lookup(c.service)
        resolved.append((c, svc, c.tier or svc.tier))

    tiers = [t for t in TIERS if any(r[2] == t for r in resolved)]
    col_of = {t: i for i, t in enumerate(tiers)}
    columns: dict[int, list] = {i: [] for i in range(len(tiers))}
    for item in resolved:
        columns[col_of[item[2]]].append(item)

    _order_by_neighbours(columns, arch)
    vpc_cols = sorted({col_of[t] for c, _, t in resolved if c.vpc})
    span = range(vpc_cols[0], vpc_cols[-1] + 1) if vpc_cols else range(0)
    r0 = max((sum(1 for it in columns[i] if not it[0].vpc) for i in span), default=0)

    placed: dict[str, tuple[int, float]] = {}  # id -> (column, row)
    heights = {}
    for i, items in columns.items():
        plain = [it for it in items if not it[0].vpc]
        boxed = [it for it in items if it[0].vpc]
        for n, it in enumerate(plain):
            placed[it[0].id] = (i, n)
        for n, it in enumerate(boxed):
            placed[it[0].id] = (i, r0 + n)
        heights[i] = len(plain) if not boxed else r0 + len(boxed)
    total = max(heights.values(), default=1)
    for i, items in columns.items():  # centre columns that do not interact with the VPC box
        if i in span or not items:
            continue
        shift = (total - heights[i]) / 2
        for it in items:
            col, row = placed[it[0].id]
            placed[it[0].id] = (col, row + shift)

    def box(col: int, row: float) -> Rect:
        return Rect(col * COL_W + (COL_W - ICON) / 2, row * ROW_H, ICON, VISUAL_H)

    rects = {cid: box(*pos) for cid, pos in placed.items()}
    by_id = {c.id: (c, s, t) for c, s, t in resolved}

    cloud_ids = [cid for cid, (_, _, t) in by_id.items() if t != "actors"]
    regional_cols = [placed[cid][0] for cid in cloud_ids if by_id[cid][1].scope == "regional"]
    rc0, rc1 = (min(regional_cols), max(regional_cols)) if regional_cols else (None, None)

    groups: list[Group] = []
    vpc_rect = None
    vpc_ids = [c.id for c, _, _ in resolved if c.vpc]
    if vpc_ids:
        vpc_rect = _union_all([rects[i] for i in vpc_ids]).pad(30, 44, 30, 22)
    region_rect = None
    in_region: set[str] = set()
    if rc0 is not None:
        in_region = {cid for cid in cloud_ids if rc0 <= placed[cid][0] <= rc1}
        region_rect = _union_all([rects[i] for i in in_region]).pad(30, 54, 30, 30)
        if vpc_rect:
            region_rect = region_rect.union(vpc_rect.pad(20, 0, 20, 20))
    if cloud_ids:
        parts = [rects[i].pad(30, 54, 30, 30) for i in cloud_ids]
        if region_rect:
            parts.append(region_rect)
        cloud_rect = _union_all(parts).pad(24, 24, 24, 24)
        groups.append(Group("cloud", "cloud", "AWS Cloud", cloud_rect, "1"))
        if region_rect:
            groups.append(Group("region", "region", arch.region, region_rect, "cloud"))
        if vpc_rect:
            suffix = " (Multi-AZ)" if arch.multi_az else ""
            groups.append(Group("vpc", "vpc", "VPC" + suffix, vpc_rect, "region"))

    nodes = []
    for c, s, t in resolved:
        if t == "actors":
            parent = "1"
        elif c.vpc:
            parent = "vpc"
        elif c.id in in_region:
            parent = "region"
        else:
            parent = "cloud"
        nodes.append(Node(c, s, *placed[c.id], rects[c.id], parent))

    everything = [n.rect for n in nodes] + [g.rect for g in groups]
    bounds = _union_all(everything)
    dx, dy = MARGIN - bounds.x, MARGIN + 40 - bounds.y  # 40px headroom for the title
    shift = lambda r: Rect(r.x + dx, r.y + dy, r.w, r.h)  # noqa: E731
    nodes = [Node(n.component, n.service, n.column, n.row, shift(n.rect), n.parent) for n in nodes]
    groups = [Group(g.id, g.kind, g.label, shift(g.rect), g.parent) for g in groups]
    return Layout(tuple(nodes), tuple(groups), bounds.w + 2 * MARGIN, bounds.h + 2 * MARGIN + 40, (MARGIN, MARGIN))


def skips_over(nodes, source_id: str, target_id: str) -> bool:
    """True when a straight arrow would cross a box in a column between source and target (draw it as an arc)."""
    by_id = {n.component.id: n for n in nodes}
    a, b = by_id[source_id], by_id[target_id]
    if b.column - a.column < 2:
        return False
    lo, hi = min(a.rect.y, b.rect.y) - 50, max(a.rect.y, b.rect.y) + 50
    return any(a.column < n.column < b.column and lo <= n.rect.y <= hi for n in nodes)
