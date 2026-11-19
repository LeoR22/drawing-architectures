"""Layout for level 1: columns of big boxes, a support band below and the story text at the bottom."""

from __future__ import annotations

from dataclasses import dataclass

from .layout import Rect
from .overview import Overview

BOX_W, BOX_H, GAP_X, GAP_Y = 250, 170, 90, 40
CHIP_W, CHIP_H = 210, 64
MARGIN = 30


@dataclass(frozen=True)
class OverviewLayout:
    boxes: dict  # capability key -> Rect
    chips: dict
    band_label: Rect | None
    story: Rect
    title_at: tuple[float, float]
    width: float
    height: float


def compute(ov: Overview) -> OverviewLayout:
    columns = sorted({b.column for b in ov.boxes})
    by_col = {c: [b for b in ov.boxes if b.column == c] for c in columns}
    rows = max((len(v) for v in by_col.values()), default=1)
    grid_h = rows * BOX_H + (rows - 1) * GAP_Y
    top = MARGIN + 100  # room for the title and the arcs that skip a column
    boxes = {}
    for i, col in enumerate(columns):
        items = by_col[col]
        col_h = len(items) * BOX_H + (len(items) - 1) * GAP_Y
        y0 = top + (grid_h - col_h) / 2
        for r, b in enumerate(items):
            boxes[b.key] = Rect(MARGIN + i * (BOX_W + GAP_X), y0 + r * (BOX_H + GAP_Y), BOX_W, BOX_H)
    width = max(len(columns) * BOX_W + (len(columns) - 1) * GAP_X, 4 * CHIP_W // 2) + 2 * MARGIN

    y = top + grid_h + 50
    chips, band_label = {}, None
    if ov.support:
        band_label = Rect(MARGIN, y, width - 2 * MARGIN, 28)
        y += 36
        per_row = max(1, int((width - 2 * MARGIN + 20) // (CHIP_W + 20)))
        for i, b in enumerate(ov.support):
            r, c = divmod(i, per_row)
            chips[b.key] = Rect(MARGIN + c * (CHIP_W + 20), y + r * (CHIP_H + 16), CHIP_W, CHIP_H)
        y += ((len(ov.support) - 1) // per_row + 1) * (CHIP_H + 16) + 10
    lines = sum(-(-len(t) // 170) for t in ov.story)
    story = Rect(MARGIN, y + 10, width - 2 * MARGIN, 44 + 19 * lines + 6 * len(ov.story))
    return OverviewLayout(boxes, chips, band_label, story, (MARGIN, MARGIN), width, story.y + story.h + MARGIN)
