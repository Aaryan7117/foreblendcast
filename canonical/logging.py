"""Structured logging configuration (TECH_APPROACH §1.1).

All QC rejections, physical-validator corrections, and shrinkage decisions
are logged as machine-readable JSON lines via structlog.

    import canonical.logging
    canonical.logging.setup()
    log = canonical.logging.get_logger(__name__)
    log.info("qc.reject", model="hres", variable="precip", reason="range_violation")
"""
from __future__ import annotations

import logging
import sys

import structlog


def setup(level: str = "INFO") -> None:
    """Call once at process start to wire structlog → JSON lines on stderr."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound logger with the module name pre-attached."""
    return structlog.get_logger(module=name)
