"""Centralized logger for autocoin-ai agents."""

from __future__ import annotations

import logging
import os


def _setup() -> None:
    root = logging.getLogger("autocoin")
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(getattr(logging, level, logging.INFO))


def get_logger(name: str) -> logging.Logger:
    _setup()
    return logging.getLogger("autocoin.%s" % name)
