"""Valsalva Maneuver analysis — Novak 2011 / Mayo Clinic protocol.

This module contains only signal processing and measurement computation.
All drawing is handled by ``autonomiclab.plotting.valsalva``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from autonomiclab.core.models import Dataset, Marker
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_THRESH = 0.5  # mmHg PAirway crossing threshold


@dataclass
class ValsalvaResult:
    """All computed measurements for a Valsalva maneuver (Novak 2011)."""

    # Phase boundaries (seconds)
    t_bl_s: Optional[float] = None      # #1 Baseline start
    t_bl_e: Optional[float] = None      # #2 Baseline end
    t_S1s:  Optional[float] = None      # #3 S1 start  (PAirway ↑ 0.5)
    t_S1e:  Optional[float] = None      # #4 S1 end    (first local SBP max)
    t_S2es: Optional[float] = None      # #5 IIe nadir time
    t_S2lmax: Optional[float] = None    # #6 S2late max time
    t_S3s:  Optional[float] = None      # #7 S3 start  (PAirway ↓ 0.5)
    t_S3e:  Optional[float] = None      # #8 S3 end    (SBP min post-release)
    t_S4e:  Optional[float] = None      # S4 end       (t_HR_max + 30 s)
    t_prt_end: Optional[float] = None   # #9  SBP returns to baseline

    # Signal values at key points
    avg_sbp:   Optional[float] = None   # Baseline mean SBP
    v_nadir:   Optional[float] = None   # IIe nadir SBP
    v_S2lmax:  Optional[float] = None   # S2late max SBP
    v_S3min:   Optional[float] = None   # S3 min SBP
    t_ov:      Optional[float] = None   # #10 SBP overshoot time
    v_ov:      Optional[float] = None   # #10 SBP overshoot value
    hr_max_t:  Optional[float] = None   # #11 HR max time
    hr_max_v:  Optional[float] = None   # #11 HR max value
    hr_min_t:  Optional[float] = None   # #12 HR min time
    hr_min_v:  Optional[float] = None   # #12 HR min value

    # Derived parameters
    A:    Optional[float] = None   # Baseline SBP − IIe nadir
    B:    Optional[float] = None   # S2late max − S3 min
    PRT:  Optional[float] = None   # Pressure Recovery Time (s)
    VR:   Optional[float] = None   # Valsalva Ratio = HR max / HR min
    BRSa: Optional[float] = None   # BRS = (A + B×0.75) / PRT


class ValsalvaAnalyzer:
    """Compute all Valsalva measurements from a Dataset."""

    def analyze(self, dataset: Dataset, markers: list[Marker]) -> ValsalvaResult:
        pa  = dataset.get_signal("PAirway")
        sys = dataset.get_signal("reSYS")
        hr  = dataset.get_signal("HR")

        if not pa or not sys or not hr:
            log.warning("Valsalva analysis: missing PAirway, reSYS or HR signal")
            return ValsalvaResult()

        t_pa, v_pa   = pa.times, pa.values
        t_sys, v_sys = sys.times, sys.values
        t_hr,  v_hr  = hr.times, hr.values

        result = ValsalvaResult()

        # ── phase boundary detection ──────────────────────────────────────────
        t_vm1 = next(
            (m.time for m in markers if "vm1" in m.label.lower()), None
        )
        t_anchor = t_vm1 if t_vm1 is not None else float(t_pa[0])

        result.t_S1s = self._pa_cross(t_pa, v_pa, t_anchor, "up")
        result.t_bl_s = (result.t_S1s - 45.0) if result.t_S1s else None
        result.t_bl_e = (result.t_S1s - 15.0) if result.t_S1s else None
        result.t_S3s  = self._pa_cross(t_pa, v_pa, result.t_S1s or t_anchor, "down")

        if result.t_S1s and result.t_S3s:
            result.t_S1e, _ = self._first_local_max_sys(t_sys, v_sys, result.t_S1s, result.t_S3s)
        if result.t_S1e and result.t_S3s:
            result.t_S2es, result.v_nadir = self._global_min_sys(t_sys, v_sys, result.t_S1e, result.t_S3s)
        if result.t_S2es and result.t_S3s:
            result.t_S2lmax, result.v_S2lmax = self._global_max_sys(t_sys, v_sys, result.t_S2es, result.t_S3s)
        if result.t_S3s:
            result.t_S3e, result.v_S3min = self._global_min_sys(t_sys, v_sys, result.t_S3s, result.t_S3s + 20.0)

        # ── HR max / HR min ───────────────────────────────────────────────────
        if result.t_S3s and len(t_hr):
            t_hr_max_end = result.t_S3s + 8.0
            m = (t_hr >= result.t_S3s) & (t_hr <= t_hr_max_end)
            if np.any(m):
                i = int(np.argmax(v_hr[m]))
                result.hr_max_t = float(t_hr[m][i])
                result.hr_max_v = float(v_hr[m][i])

        result.t_S4e = (result.hr_max_t + 30.0) if result.hr_max_t else None

        if result.hr_max_t and result.t_S4e and len(t_hr):
            m = (t_hr >= result.hr_max_t) & (t_hr <= result.t_S4e)
            if np.any(m):
                i = int(np.argmin(v_hr[m]))
                result.hr_min_t = float(t_hr[m][i])
                result.hr_min_v = float(v_hr[m][i])

        # ── SBP baseline + derived A, B, PRT ─────────────────────────────────
        if result.t_bl_s and result.t_bl_e:
            result.avg_sbp = self._mean_sys(t_sys, v_sys, result.t_bl_s, result.t_bl_e)

        if result.t_S2es and result.v_nadir is not None and result.avg_sbp:
            result.A = result.avg_sbp - result.v_nadir

        if result.t_S2lmax and result.v_S2lmax and result.t_S3e and result.v_S3min is not None:
            result.B = result.v_S2lmax - result.v_S3min

        if result.t_S3e and result.avg_sbp and len(t_sys):
            result.t_prt_end, result.PRT = self._compute_prt(
                t_sys, v_sys, result.t_S3e, result.avg_sbp
            )

        if result.t_S3e and result.t_S4e:
            result.t_ov, result.v_ov = self._global_max_sys(t_sys, v_sys, result.t_S3e, result.t_S4e)

        if result.hr_max_v and result.hr_min_v and result.hr_min_v > 0:
            result.VR = result.hr_max_v / result.hr_min_v

        if result.A is not None and result.B is not None and result.PRT and result.PRT > 0:
            result.BRSa = (result.A + result.B * 0.75) / result.PRT

        log.debug(
            "Valsalva: A=%.1f B=%.1f PRT=%.2f VR=%.2f BRSa=%s",
            result.A or 0, result.B or 0, result.PRT or 0,
            result.VR or 0, f"{result.BRSa:.2f}" if result.BRSa else "N/A",
        )
        return result

    # ── private signal helpers ────────────────────────────────────────────────

    @staticmethod
    def _mean_sys(t: np.ndarray, v: np.ndarray, ta: float, tb: float) -> Optional[float]:
        m = (t >= ta) & (t <= tb)
        return float(np.mean(v[m])) if np.any(m) else None

    @staticmethod
    def _global_min_sys(
        t: np.ndarray, v: np.ndarray, ta: float, tb: float
    ) -> tuple[Optional[float], Optional[float]]:
        m = (t >= ta) & (t <= tb)
        if not np.any(m):
            return None, None
        ts, vs = t[m], v[m]
        i = int(np.argmin(vs))
        return float(ts[i]), float(vs[i])

    @staticmethod
    def _global_max_sys(
        t: np.ndarray, v: np.ndarray, ta: float, tb: float
    ) -> tuple[Optional[float], Optional[float]]:
        m = (t >= ta) & (t <= tb)
        if not np.any(m):
            return None, None
        ts, vs = t[m], v[m]
        i = int(np.argmax(vs))
        return float(ts[i]), float(vs[i])

    @staticmethod
    def _first_local_max_sys(
        t: np.ndarray, v: np.ndarray, ta: float, tb: float
    ) -> tuple[Optional[float], Optional[float]]:
        m = (t >= ta) & (t <= tb)
        if not np.any(m):
            return None, None
        vs, ts = v[m], t[m]
        for i in range(1, len(vs) - 1):
            if vs[i] > vs[i - 1] and vs[i] > vs[i + 1]:
                return float(ts[i]), float(vs[i])
        # Fallback to global max
        i = int(np.argmax(vs))
        return float(ts[i]), float(vs[i])

    @staticmethod
    def _pa_cross(
        t_pa: np.ndarray,
        v_pa: np.ndarray,
        t_from: float,
        direction: str,
        verify_level: float = 5.0,
        verify_dur: float = 1.0,
    ) -> Optional[float]:
        """Find first PAirway crossing of THRESH after t_from.

        For 'up': verifies signal reaches verify_level within verify_dur s
        (avoids false triggers on brief spikes).
        Returns interpolated crossing time.
        """
        m = t_pa > t_from
        if not np.any(m):
            return None
        ts, vs = t_pa[m], v_pa[m]

        if direction == "up":
            cands = np.where((vs[:-1] < _THRESH) & (vs[1:] >= _THRESH))[0]
        else:
            cands = np.where((vs[:-1] >= _THRESH) & (vs[1:] < _THRESH))[0]

        for ci in cands:
            t1, v1 = float(ts[ci]),   float(vs[ci])
            t2, v2 = float(ts[ci + 1]), float(vs[ci + 1])
            frac = (_THRESH - v1) / (v2 - v1) if (v2 - v1) != 0 else 0.0
            t_cross = t1 + frac * (t2 - t1)

            if direction == "up":
                win = (ts >= t_cross) & (ts <= t_cross + verify_dur)
                if np.any(win) and np.max(vs[win]) >= verify_level:
                    return t_cross
            else:
                return t_cross

        # Fallback: return first crossing without verification
        if len(cands) > 0:
            ci = cands[0]
            t1, v1 = float(ts[ci]), float(vs[ci])
            t2, v2 = float(ts[ci + 1]), float(vs[ci + 1])
            frac = (_THRESH - v1) / (v2 - v1) if (v2 - v1) != 0 else 0.0
            return t1 + frac * (t2 - t1)
        return None

    @staticmethod
    def _compute_prt(
        t: np.ndarray, v: np.ndarray, t_s3e: float, avg_sbp: float
    ) -> tuple[Optional[float], Optional[float]]:
        """Compute Pressure Recovery Time from S3 nadir to SBP returning to baseline."""
        m = t > t_s3e
        if not np.any(m):
            return None, None
        ta, va = t[m], v[m]
        ci_arr = np.where(va >= avg_sbp)[0]
        if not len(ci_arr):
            return None, None
        ci = ci_arr[0]
        if ci > 0:
            t1, v1 = float(ta[ci - 1]), float(va[ci - 1])
            t2, v2 = float(ta[ci]),     float(va[ci])
            frac = (avg_sbp - v1) / (v2 - v1) if (v2 - v1) != 0 else 0.0
            t_prt_end = t1 + frac * (t2 - t1)
        else:
            t_prt_end = float(ta[0])
        return t_prt_end, t_prt_end - t_s3e
