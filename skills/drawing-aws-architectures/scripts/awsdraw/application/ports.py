"""Ports (interfaces) the use cases depend on. Adapters implement them."""

from __future__ import annotations

from typing import Protocol

from ..domain.layout import Layout
from ..domain.models import Architecture, Requirements


class Planner(Protocol):
    def plan(self, requirements: Requirements) -> Architecture: ...


class DiagramRenderer(Protocol):
    def render(self, architecture: Architecture, layout: Layout) -> str: ...


class FileWriter(Protocol):
    def write(self, path: str, content: str) -> str: ...


class EditorOpener(Protocol):
    def open(self, path: str) -> bool: ...
