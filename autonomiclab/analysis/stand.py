"""Stand Test analysis (placeholder — no numerical analysis yet)."""

from __future__ import annotations

from dataclasses import dataclass

from autonomiclab.core.models import Dataset, Marker
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class StandResult:
    """Placeholder result for Stand Test analysis."""
    pass


class StandAnalyzer:
    def analyze(self, dataset: Dataset, markers: list[Marker]) -> StandResult:
        log.debug("Stand Test analysis: no numerical analysis implemented yet")
        return StandResult()
