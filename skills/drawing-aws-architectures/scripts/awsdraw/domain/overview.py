"""Level 1 of the diagram: the same architecture told in plain language with four blocks. Pure."""

from __future__ import annotations

from dataclasses import dataclass

from . import capabilities, catalog
from .models import Architecture


@dataclass(frozen=True)
class Box:
    key: str
    title: str
    does: str
    column: int
    items: tuple[str, ...]  # plain-language parts inside this block
    services: tuple[str, ...]  # AWS names, shown as small print


@dataclass(frozen=True)
class Link:
    source: str  # box key
    target: str
    step: int


@dataclass(frozen=True)
class Overview:
    title: str
    boxes: tuple[Box, ...]  # main blocks, left to right
    support: tuple[Box, ...]  # always-on band: security, monitoring...
    links: tuple[Link, ...]
    story: tuple[str, ...]  # numbered sentences anyone can read aloud


def _add(store: dict, key: str, item: str, service: str) -> None:
    items, services = store.setdefault(key, ([], []))
    if item not in items:
        items.append(item)
    if service not in services:
        services.append(service)


def build(arch: Architecture) -> Overview:
    blocks: dict[str, tuple[list, list]] = {}
    support: dict[str, tuple[list, list]] = {}
    block_of_component: dict[str, str | None] = {}
    for comp in arch.components:
        svc = catalog.lookup(comp.service)
        cap = capabilities.of(svc.key)
        block = capabilities.block_of(cap.key)
        block_of_component[comp.id] = block.key if block else None
        if block:
            _add(blocks, block.key, cap.title, svc.label)
        else:
            _add(support, cap.key, cap.title, svc.label)

    main = sorted((capabilities.BLOCKS[k] for k in blocks), key=lambda b: b.column)
    boxes = tuple(Box(b.key, b.title, b.does, b.column, tuple(blocks[b.key][0]), tuple(blocks[b.key][1])) for b in main)
    band = tuple(
        Box(k, capabilities.CAPABILITIES[k].title, capabilities.CAPABILITIES[k].does, capabilities.SUPPORT, (), tuple(v[1]))
        for k, v in support.items()
    )

    by_key = {b.key: b for b in boxes}
    links, story, seen, pairs = [], [], set(), []
    for flow in arch.flows:
        a, b = block_of_component[flow.source], block_of_component[flow.target]
        if a is None or b is None or a == b or (a, b) in seen:
            continue
        seen.add((a, b))
        pairs.append((a, b))
    pairs.sort(key=lambda ab: (by_key[ab[0]].column, by_key[ab[1]].column))  # reads left to right
    for step, (a, b) in enumerate(pairs, 1):
        links.append(Link(a, b, step))
        target = by_key[b]
        inside = f" Incluye: {', '.join(i.lower() for i in target.items)}." if target.key != "people" else ""
        story.append(f"{step}. {by_key[a].title} → {target.title}: {target.does}.{inside}")
    return Overview(arch.title, boxes, band, tuple(links), tuple(story))
