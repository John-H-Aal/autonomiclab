"""Centralised logging configuration for AutonomicLab.

Usage in every module::

    from autonomiclab.utils.logger import get_logger
    log = get_logger(__name__)

Call ``configure_root_logger()`` once at startup (in ``__main__.py``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


_FMT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_DATE = "%H:%M:%S"


def configure_root_logger(
    log_file: Optional[Path] = None,
    level: int = logging.DEBUG,
) -> None:
    """Configure the root logger. Call once at application startup."""
    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return  # already configured

    fmt = logging.Formatter(_FMT, datefmt=_DATE)

    handler: logging.Handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    root.addHandler(handler)

    if log_file is not None:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Lazily inherits root configuration."""
    return logging.getLogger(name)
