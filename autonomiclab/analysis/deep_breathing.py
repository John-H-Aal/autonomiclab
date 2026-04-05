"""Deep Breathing / RSA analysis — Novak / Rasmussen protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.signal import find_peaks

from autonomiclab.core.models import Dataset, Marker
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

N_SELECT = 6  # number of top cycles to include in clinical mean


@dataclass
class RSACycle:
    """One inspiration-peak / expiration-trough pair."""
    cycle: int
    max_t: float
    max_v: float
    min_t: float
    min_v: float
    rsa: float   # ΔHR = max_v − min_v


@dataclass
class DeepBreathingResult:
    """All RSA cycle data for a deep-breathing maneuver."""
    cycles: list[RSACycle] = field(default_factory=list)
    top6: set[int] = field(default_factory=set)
    avg_rsa_all:  float = 0.0
    avg_rsa_top6: float = 0.0
    mean_max_all: float = 0.0
    mean_min_all: float = 0.0
    mean_max_top: float = 0.0
    mean_min_top: float = 0.0
    n_sel: int = 0
    t_dbm2: Optional[float] = None
    t_dbm3: Optional[float] = None

    @property
    def valid_cycles(self) -> list[RSACycle]:
        return [c for c in self.cycles if c.rsa > 0]

    @property
    def top6_cycles(self) -> list[RSACycle]:
        return [c for c in self.valid_cycles if c.cycle in self.top6]


class DeepBreathingAnalyzer:
    """Detect RSA cycles and compute ΔHR statistics."""

    def analyze(self, dataset: Dataset, markers: list[Marker]) -> DeepBreathingResult:
        hr = dataset.get_signal("HR")
        if not hr:
            log.warning("Deep breathing analysis: HR signal not found")
            return DeepBreathingResult()

        t_hr = hr.times
        v_hr = hr.values

        result = DeepBreathingResult()
        result.t_dbm2 = next((m.time for m in markers if "dbm2" in m.label.lower()), None)
        result.t_dbm3 = next((m.time for m in markers if "dbm3" in m.label.lower()), None)

        if not result.t_dbm2 or not result.t_dbm3:
            log.info("Deep breathing: DBM2/DBM3 markers not found — no RSA analysis")
            return result

        # ── peak / trough detection within guided breathing window ────────────
        m_win = (t_hr >= result.t_dbm2) & (t_hr <= result.t_dbm3)
        t_win = t_hr[m_win]
        v_win = v_hr[m_win]

        if len(t_win) <= 4:
            log.warning("Deep breathing: too few HR samples in DBM window")
            return result

        dt = float(np.median(np.diff(t_win)))
        min_dist = max(1, int(4.0 / dt))

        peaks_i,   _ = find_peaks( v_win, distance=min_dist, prominence=3.0)
        troughs_i, _ = find_peaks(-v_win, distance=min_dist, prominence=3.0)

        log.debug("RSA peaks at:   %s", [round(float(t_win[i]), 1) for i in peaks_i])
        log.debug("RSA troughs at: %s", [round(float(t_win[i]), 1) for i in troughs_i])

        # ── pair each peak with the first unused trough that follows it ───────
        used_troughs: set[int] = set()
        cycles: list[RSACycle] = []
        cycle_n = 1

        for pi in peaks_i:
            best_ti = next(
                (ti for ti in troughs_i if ti > pi and ti not in used_troughs), None
            )
            if best_ti is None:
                continue
            used_troughs.add(best_ti)

            cycles.append(RSACycle(
                cycle=cycle_n,
                max_t=float(t_win[pi]),
                max_v=float(v_win[pi]),
                min_t=float(t_win[best_ti]),
                min_v=float(v_win[best_ti]),
                rsa=float(v_win[pi] - v_win[best_ti]),
            ))
            cycle_n += 1

        result.cycles = cycles
        log.info("RSA cycles found: %d", len(cycles))

        if not cycles:
            return result

        self._recompute_stats(result)

        log.info(
            "RSA mean ΔHR: all=%.1f  top%d=%.1f bpm",
            result.avg_rsa_all, result.n_sel, result.avg_rsa_top6,
        )
        return result

    def apply_cycle_overrides(
        self,
        result: DeepBreathingResult,
        dataset: Dataset,
        stored_cycles: list[dict],
    ) -> None:
        """Replace auto-detected cycles with manually overridden ones and recompute stats.

        ``stored_cycles`` is a list of dicts with keys:
        ``cycle, max_t, min_t``  (values are snapped to the actual HR signal).
        """
        hr = dataset.get_signal("HR")
        if not hr:
            return
        t_hr = np.asarray(hr.times)
        v_hr = np.asarray(hr.values)

        def _snap(t: float) -> tuple[float, float]:
            i = int(np.argmin(np.abs(t_hr - t)))
            return float(t_hr[i]), float(v_hr[i])

        cycles: list[RSACycle] = []
        for i, d in enumerate(stored_cycles, start=1):
            max_t, max_v = _snap(d["max_t"])
            min_t, min_v = _snap(d["min_t"])
            cycles.append(RSACycle(
                cycle=i,
                max_t=max_t, max_v=max_v,
                min_t=min_t, min_v=min_v,
                rsa=max_v - min_v,
            ))

        result.cycles = cycles
        self._recompute_stats(result)

    @staticmethod
    def _recompute_stats(result: DeepBreathingResult) -> None:
        """Recompute top-6, means and averages from result.cycles in place."""
        valid = result.valid_cycles
        if not valid:
            result.top6 = set()
            result.n_sel = result.avg_rsa_all = result.avg_rsa_top6 = 0.0
            result.mean_max_all = result.mean_min_all = 0.0
            result.mean_max_top = result.mean_min_top = 0.0
            return

        top6_set = {
            c.cycle for c in sorted(valid, key=lambda x: x.rsa, reverse=True)[:N_SELECT]
        }
        top6_cycles = [c for c in valid if c.cycle in top6_set]
        n_sel = min(N_SELECT, len(valid))

        result.top6         = top6_set
        result.n_sel        = n_sel
        result.avg_rsa_all  = float(np.mean([c.rsa for c in valid]))
        result.avg_rsa_top6 = float(np.mean([c.rsa for c in top6_cycles])) if top6_cycles else 0.0
        result.mean_max_all = float(np.mean([c.max_v for c in valid]))
        result.mean_min_all = float(np.mean([c.min_v for c in valid]))
        result.mean_max_top = float(np.mean([c.max_v for c in top6_cycles])) if top6_cycles else 0.0
        result.mean_min_top = float(np.mean([c.min_v for c in top6_cycles])) if top6_cycles else 0.0
