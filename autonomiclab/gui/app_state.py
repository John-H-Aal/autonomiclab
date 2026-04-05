"""AppState — single source of truth for mutable application state."""

from __future__ import annotations

from dataclasses import dataclass, field

from autonomiclab.core.models import Dataset


@dataclass
class AppState:
    """All mutable runtime state owned by one object.

    Passed by reference to both ``MainWindow`` and ``AppController`` so both
    always see the same values without extra synchronisation.
    """

    dataset:           Dataset | None      = None
    overrides:         dict[str, dict]     = field(default_factory=dict)
    analysis_mode:     str                 = "auto"   # "auto" | "manual"
    last_protocol_key: str | None          = None
    last_result:       object | None       = None
