"""Agent profile: classify components into the zones of a typical agentic system. Pure.

Zones: users, frontend application, agent runtime, model runtime, memory (short/long term),
tools (databases, APIs, services, files) reached through a communication protocol (e.g. MCP).
A component can carry an explicit `role`; otherwise it is inferred from its generic kind.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import system_design
from .models import Architecture, Component

ROLES = ("users", "frontend", "agent", "model", "memory_short", "memory_long",
         "tool_database", "tool_api", "tool_service", "tool_files", "support")

_BY_KIND = {
    "actor": "users", "client": "users", "mobile": "users",
    "cdn": "frontend", "dns": "frontend", "hosting": "frontend", "gateway": "frontend", "lb": "frontend",
    "firewall": "frontend", "auth": "frontend",
    "agent": "agent", "model": "model", "cache": "memory_short", "search": "memory_long",
    "db": "tool_database", "warehouse": "tool_database", "analytics": "tool_database", "bi": "tool_database",
    "object": "tool_files",
    "service": "tool_service", "queue": "tool_service", "pubsub": "tool_service", "bus": "tool_service",
    "workflow": "tool_service", "stream": "tool_service",
    "observability": "support", "audit": "support", "secrets": "support", "security": "support",
    "backup": "support", "iac": "support",
}


@dataclass(frozen=True)
class AgentView:
    zones: dict  # role -> tuple[Component, ...]


def is_agentic(arch: Architecture) -> bool:
    return arch.profile == "agents" or any(c.role == "agent" for c in arch.components)


def _default_role(component: Component) -> str:
    return _BY_KIND[system_design.kind_of(component).key]


def classify(arch: Architecture) -> AgentView:
    roles = {c.id: (c.role if c.role in ROLES else _default_role(c)) for c in arch.components}
    if not any(r == "agent" for r in roles.values()):
        model_ids = {i for i, r in roles.items() if r == "model"}
        services = [c for c in arch.components if roles[c.id] == "tool_service"]
        linked = [c for c in services if any((f.source == c.id and f.target in model_ids) or (f.target == c.id and f.source in model_ids) for f in arch.flows)]
        chosen = (linked or services or [None])[0]
        if chosen is not None:
            roles[chosen.id] = "agent"
    zones = {r: tuple(c for c in arch.components if roles[c.id] == r) for r in ROLES}
    return AgentView(zones)
