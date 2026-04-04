"""Protocol registry — maps phase names to analyzer + plotter pairs.

Usage::

    from autonomiclab.plotting.registry import resolve_protocol, PROTOCOL_REGISTRY

    key = resolve_protocol("Valsalva 1")       # → "valsalva"
    if key:
        handlers = PROTOCOL_REGISTRY[key]
        result = handlers["analyzer"].analyze(dataset, dataset.markers)
        handlers["plotter"].plot(plot_widget, dataset, result, t_start, t_end,
                                  output_dir=dataset.path)
"""

from __future__ import annotations

from typing import Any

from autonomiclab.analysis.deep_breathing import DeepBreathingAnalyzer
from autonomiclab.analysis.stand import StandAnalyzer
from autonomiclab.analysis.valsalva import ValsalvaAnalyzer
from autonomiclab.plotting.deep_breathing import DeepBreathingPlotter
from autonomiclab.plotting.stand import StandPlotter
from autonomiclab.plotting.valsalva import ValsalvaPlotter

PROTOCOL_REGISTRY: dict[str, dict[str, Any]] = {
    "valsalva": {
        "analyzer": ValsalvaAnalyzer(),
        "plotter":  ValsalvaPlotter(),
    },
    "stand": {
        "analyzer": StandAnalyzer(),
        "plotter":  StandPlotter(),
    },
    "deep breath": {
        "analyzer": DeepBreathingAnalyzer(),
        "plotter":  DeepBreathingPlotter(),
    },
}

# Keyword → registry key mapping (first match wins)
_KEYWORDS: list[tuple[str, str]] = [
    ("valsalva", "valsalva"),
    ("stand",    "stand"),
    ("deep",     "deep breath"),
    ("breath",   "deep breath"),
]


def resolve_protocol(phase_name: str) -> str | None:
    """Map a region/phase name to a registry key, or None for overview."""
    lo = phase_name.lower()
    for keyword, key in _KEYWORDS:
        if keyword in lo:
            return key
    return None
