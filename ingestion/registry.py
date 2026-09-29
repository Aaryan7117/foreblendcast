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
    """Import all adapter modules to trigger registration, then attach the GRIB2 sources."""
    from ingestion import ecmwf, graphcast, pangu  # noqa: F401
    from ingestion import grib2
    grib2.register_grib_sources()


def for_variable(variable: str) -> list[str]:
    """Names of the registered adapters that provide a variable."""
    return [name for name, a in _ADAPTERS.items() if variable in a.variables]
