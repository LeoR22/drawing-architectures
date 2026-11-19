"""Core entities of a high-level AWS architecture. Pure Python, no I/O."""

from __future__ import annotations

from dataclasses import dataclass

TIERS = ("actors", "edge", "app", "data", "ops")


@dataclass(frozen=True)
class Component:
    id: str
    service: str  # catalog key, e.g. "lambda"
    label: str = ""
    tier: str | None = None  # None -> the catalog default for the service
    vpc: bool = False
    role: str | None = None  # optional agent-profile role, see domain/agents.py


@dataclass(frozen=True)
class Flow:
    source: str
    target: str
    label: str = ""
    is_async: bool = False  # drawn dashed


@dataclass(frozen=True)
class Architecture:
    title: str
    components: tuple[Component, ...]
    flows: tuple[Flow, ...]
    region: str = "us-east-1"
    multi_az: bool = False
    profile: str | None = None  # None (general) or "agents"


@dataclass(frozen=True)
class Requirements:
    """What the user asked for, already reduced to text (+ optional images)."""

    text: str
    images: tuple[tuple[str, bytes], ...] = ()


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # "error" | "warning"
    message: str
