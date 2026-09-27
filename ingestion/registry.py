"""Adapter registry (B4). One-line registration for new models."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ingestion.base import Adapter

_ADAPTERS: dict[str, "Adapter"] = {}


def register(adapter: "Adapter") -> "Adapter":
    _ADAPTERS[adapter.name] = adapter
    return adapter


def get(name: str) -> "Adapter":
    return _ADAPTERS[name]


def all_adapters() -> dict[str, "Adapter"]:
    return dict(_ADAPTERS)


def load_all() -> None:
    """Import all adapter modules to trigger registration."""
    from ingestion import ecmwf, graphcast  # noqa: F401
