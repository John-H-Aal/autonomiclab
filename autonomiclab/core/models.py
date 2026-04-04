"""Core data models for AutonomicLab."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class Signal:
    """A single physiological time-series signal."""
    name: str
    times: np.ndarray
    values: np.ndarray
    unit: str = ""

    @property
    def t_start(self) -> float:
        return float(self.times[0]) if len(self.times) else 0.0

    @property
    def t_end(self) -> float:
        return float(self.times[-1]) if len(self.times) else 0.0

    def __bool__(self) -> bool:
        return len(self.times) > 0

    def slice(self, t_start: float, t_end: float) -> Signal:
        """Return a new Signal restricted to [t_start, t_end]."""
        mask = (self.times >= t_start) & (self.times <= t_end)
        return Signal(self.name, self.times[mask], self.values[mask], self.unit)


@dataclass
class Marker:
    """A single event marker with time, label, and protocol phase."""
    time: float
    label: str
    phase: str


@dataclass
class Dataset:
    """All loaded data for one Finapres recording session."""
    path: Path
    prefix: str
    signals: dict[str, Signal] = field(default_factory=dict)
    markers: list[Marker] = field(default_factory=list)
    region_markers: dict[str, tuple[float, float]] = field(default_factory=dict)

    def get_signal(self, name: str) -> Optional[Signal]:
        """Return Signal by name, or None if not present."""
        return self.signals.get(name)

    def has_signal(self, name: str) -> bool:
        return name in self.signals and bool(self.signals[name])

    def phase_window(self, phase_name: str) -> tuple[float, float]:
        """Return (t_start, t_end) for a named phase, or full recording range."""
        if phase_name in self.region_markers:
            return self.region_markers[phase_name]
        hr = self.signals.get("HR")
        if hr:
            return hr.t_start, hr.t_end
        return 0.0, 1500.0
