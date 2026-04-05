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

    # Calibration warnings: list of region names where PhysioCalActive was 1
    cal_warnings: list = None  # e.g. ["Baseline", "Phase IV"]

    def __post_init__(self):
        if self.cal_warnings is None:
            self.cal_warnings = []


class ValsalvaAnalyzer:
    """Compute all Valsalva measurements from a Dataset."""

    def analyze(
        self,
        dataset: Dataset,
        markers: list[Marker],
        t_start: Optional[float] = None,
        t_end: Optional[float] = None,
    ) -> ValsalvaResult:
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
        # Restrict marker search to the selected region so multiple Valsalva
        # sections each find their own markers.
        window_markers = (
            [m for m in markers if t_start <= m.time <= t_end]
            if t_start is not None and t_end is not None
            else markers
        )
        t_vm1 = next(
            (m.time for m in window_markers if "vm1" in m.label.lower()), None
        )
        t_anchor = t_vm1 if t_vm1 is not None else float(t_pa[0])

        # ── prefer manually placed "M Phase X" markers where available ─────────
        def _m(label_fragment: str) -> Optional[float]:
            """Return time of first window marker whose label contains the fragment."""
            frag = label_fragment.lower()
            return next(
                (m.time for m in window_markers if frag in m.label.lower()), None
            )

        result.t_S1s = self._pa_cross(t_pa, v_pa, t_anchor, "up")
        result.t_bl_s = (result.t_S1s - 45.0) if result.t_S1s else None
        result.t_bl_e = (result.t_S1s - 15.0) if result.t_S1s else None
        result.t_S3s  = self._pa_cross(t_pa, v_pa, result.t_S1s or t_anchor, "down")

        if result.t_S1s and result.t_S3s:
            result.t_S1e, _ = self._first_local_max_sys(t_sys, v_sys, result.t_S1s, result.t_S3s)
        # Manual marker overrides algorithmic detection for Phase I end
        result.t_S1e = _m("phase 1: end") or result.t_S1e
        if result.t_S1e and result.t_S3s:
            result.t_S2es, result.v_nadir = self._global_min_sys(t_sys, v_sys, result.t_S1e, result.t_S3s)
        if result.t_S2es and result.t_S3s:
            result.t_S2lmax, result.v_S2lmax = self._global_max_sys(t_sys, v_sys, result.t_S2es, result.t_S3s)
        if result.t_S3s:
            result.t_S3e, result.v_S3min = self._global_min_sys(t_sys, v_sys, result.t_S3s, result.t_S3s + 20.0)

        # ── HR max: Phase IIe nadir → 5 s after strain release (t_S3s + 5 s)
        # Literature (Novak 2011, PMC8897824) places peak tachycardia in Phase II
        # late / early Phase III, within ~1–3 s of strain release.  Phase IV is
        # bradycardia-dominant, so we anchor on t_S3s (PAirway crossing) rather
        # than t_S3e (SBP nadir) and add a 5 s tolerance for latency variability.
        _hr_search_end = (result.t_S3s + 5.0) if result.t_S3s else (result.t_S3e + 5.0 if result.t_S3e else None)
        if result.t_S2es and _hr_search_end and len(t_hr):
            m = (t_hr >= result.t_S2es) & (t_hr <= _hr_search_end)
            if np.any(m):
                i = int(np.argmax(v_hr[m]))
                result.hr_max_t = float(t_hr[m][i])
                result.hr_max_v = float(v_hr[m][i])

        # Phase IV ends 30 s after strain release (t_S3s).
        # "M Phase 4: End" marks something else in the GAT protocol and must not
        # override the clinical 30-second PIV window.
        result.t_S4e = (
            (result.t_S3s + 30.0) if result.t_S3s else
            (result.hr_max_t + 30.0) if result.hr_max_t else None
        )

        if result.hr_max_t and result.t_S4e and len(t_hr):
            m = (t_hr >= result.hr_max_t) & (t_hr <= result.t_S4e)
            if np.any(m):
                i = int(np.argmin(v_hr[m]))
                result.hr_min_t = float(t_hr[m][i])
                result.hr_min_v = float(v_hr[m][i])

        # ── Finapres calibration guard ────────────────────────────────────────
        # Check PhysioCalActive in every critical window.  Contaminated windows
        # are recorded in result.cal_warnings; Phase IV contamination also
        # suppresses PIV-dependent derived values entirely.
        cal_sig = dataset.get_signal("PhysioCalActive")

        def _cal_active(ta: Optional[float], tb: Optional[float]) -> bool:
            """True if PhysioCalActive == 1 at any sample in [ta, tb]."""
            if cal_sig is None or ta is None or tb is None:
                return False
            t_c, v_c = cal_sig.times, cal_sig.values
            mask = (t_c >= ta) & (t_c <= tb)
            return bool(np.any(mask) and np.any(v_c[mask] > 0.5))

        if _cal_active(result.t_bl_s, result.t_bl_e):
            result.cal_warnings.append("Baseline")
            log.warning("Finapres calibration during Baseline (%.1f – %.1f s)",
                        result.t_bl_s, result.t_bl_e)

        # Check the entire post-release window (PIII + PIV) in one pass.
        # If calibration hits anywhere after strain release, both PIII and PIV
        # are unreliable — suppress all derived post-release values.
        _post_release_contaminated = _cal_active(result.t_S3s, result.t_S4e)
        if _post_release_contaminated:
            result.cal_warnings.append("Phase III+IV")
            log.warning("Finapres calibration during post-release window "
                        "(%.1f – %.1f s) — PIII, PIV, PRT and overshoot suppressed",
                        result.t_S3s, result.t_S4e)
            result.t_S3e    = None   # removes PIII shade + PRT anchor
            result.v_S3min  = None
            result.t_S4e    = None   # removes PIV shade
            result.hr_min_t = None
            result.hr_min_v = None

        # ── SBP baseline + derived A, B, PRT ─────────────────────────────────
        if result.t_bl_s and result.t_bl_e:
            result.avg_sbp = self._mean_sys(t_sys, v_sys, result.t_bl_s, result.t_bl_e)

        if result.t_S2es and result.v_nadir is not None and result.avg_sbp:
            result.A = result.avg_sbp - result.v_nadir

        # B = max SBP(S2 late) − min SBP(S2 late); the min of S2 late is the IIe nadir
        if result.t_S2lmax and result.v_S2lmax and result.v_nadir is not None:
            result.B = result.v_S2lmax - result.v_nadir

        if not _post_release_contaminated:
            if result.t_S3e and result.avg_sbp and len(t_sys):
                # Cap PRT search at 20 s after t_S3e.
                result.t_prt_end, result.PRT = self._compute_prt(
                    t_sys, v_sys, result.t_S3e, result.avg_sbp,
                    t_end=result.t_S3e + 20.0,
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

    def recompute_from_baseline(
        self, result: ValsalvaResult, dataset: Dataset
    ) -> None:
        """Recompute all values that depend on t_bl_s / t_bl_e (after a manual override)."""
        sys = dataset.get_signal("reSYS")
        if not sys or result.t_bl_s is None or result.t_bl_e is None:
            return
        t_sys = np.asarray(sys.times)
        v_sys = np.asarray(sys.values)

        result.avg_sbp = self._mean_sys(t_sys, v_sys, result.t_bl_s, result.t_bl_e)
        if result.avg_sbp is not None and result.v_nadir is not None:
            result.A = result.avg_sbp - result.v_nadir
        if result.t_S3e and result.avg_sbp:
            result.t_prt_end, result.PRT = self._compute_prt(
                t_sys, v_sys, result.t_S3e, result.avg_sbp
            )
        if result.A is not None and result.B is not None and result.PRT and result.PRT > 0:
            result.BRSa = (result.A + result.B * 0.75) / result.PRT

    def apply_point_overrides(
        self,
        result: ValsalvaResult,
        dataset: Dataset,
        overrides: dict,
    ) -> None:
        """Apply manually overridden marker positions and recompute downstream.

        ``overrides`` maps ValsalvaResult field names to new time values,
        e.g. ``{"t_S1e": 136.0, "t_S2es": 142.5}``.
        Fields are applied in dependency order so each recomputation uses the
        most up-to-date values.
        """
        sys_sig = dataset.get_signal("reSYS")
        hr_sig  = dataset.get_signal("HR")
        if not sys_sig:
            return

        t_sys = np.asarray(sys_sig.times)
        v_sys = np.asarray(sys_sig.values)
        t_hr  = np.asarray(hr_sig.times)  if hr_sig else np.array([])
        v_hr  = np.asarray(hr_sig.values) if hr_sig else np.array([])

        def _interp_sys(t: float) -> float:
            return float(np.interp(t, t_sys, v_sys))

        for field in ("t_S1e", "t_S2es", "t_S2lmax", "t_S3s", "t_S3e",
                      "t_ov", "hr_max_t", "hr_min_t"):
            if field not in overrides:
                continue
            t_new = float(overrides[field])
            setattr(result, field, t_new)

            if field == "t_S1e":
                if result.t_S3s:
                    result.t_S2es, result.v_nadir = self._global_min_sys(
                        t_sys, v_sys, t_new, result.t_S3s)
                    if result.t_S2es:
                        result.t_S2lmax, result.v_S2lmax = self._global_max_sys(
                            t_sys, v_sys, result.t_S2es, result.t_S3s)

            elif field == "t_S2es":
                result.v_nadir = _interp_sys(t_new)
                if result.t_S3s:
                    result.t_S2lmax, result.v_S2lmax = self._global_max_sys(
                        t_sys, v_sys, t_new, result.t_S3s)

            elif field == "t_S2lmax":
                result.v_S2lmax = _interp_sys(t_new)

            elif field == "t_S3s":
                if result.t_S1e:
                    result.t_S2es, result.v_nadir = self._global_min_sys(
                        t_sys, v_sys, result.t_S1e, t_new)
                    if result.t_S2es:
                        result.t_S2lmax, result.v_S2lmax = self._global_max_sys(
                            t_sys, v_sys, result.t_S2es, t_new)
                result.t_S3e, result.v_S3min = self._global_min_sys(
                    t_sys, v_sys, t_new, t_new + 20.0)
                result.t_S4e = t_new + 30.0

            elif field == "t_S3e":
                result.v_S3min = _interp_sys(t_new)

            elif field == "t_ov":
                result.v_ov = _interp_sys(t_new)

            elif field == "hr_max_t":
                if len(t_hr):
                    result.hr_max_v = float(np.interp(t_new, t_hr, v_hr))
                    # Only auto-place hr_min if the investigator hasn't pinned it
                    if result.t_S4e and "hr_min_t" not in overrides:
                        result.hr_min_t, result.hr_min_v = self._global_min_sys(
                            t_hr, v_hr, t_new, result.t_S4e)

            elif field == "hr_min_t":
                if len(t_hr):
                    result.hr_min_v = float(np.interp(t_new, t_hr, v_hr))

        # Recompute all derived scalars
        if result.t_S2es and result.v_nadir is not None and result.avg_sbp:
            result.A = result.avg_sbp - result.v_nadir
        if result.t_S2lmax and result.v_S2lmax and result.v_nadir is not None:
            result.B = result.v_S2lmax - result.v_nadir
        if result.t_S3e and result.avg_sbp and len(t_sys):
            result.t_prt_end, result.PRT = self._compute_prt(
                t_sys, v_sys, result.t_S3e, result.avg_sbp,
                t_end=result.t_S3e + 20.0,
            )
        if result.t_S3e and result.t_S4e and "t_ov" not in overrides:
            result.t_ov, result.v_ov = self._global_max_sys(
                t_sys, v_sys, result.t_S3e, result.t_S4e)
        if result.hr_max_v and result.hr_min_v and result.hr_min_v > 0:
            result.VR = result.hr_max_v / result.hr_min_v
        if result.A is not None and result.B is not None and result.PRT and result.PRT > 0:
            result.BRSa = (result.A + result.B * 0.75) / result.PRT

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
        t: np.ndarray, v: np.ndarray, t_s3e: float, avg_sbp: float,
        t_end: Optional[float] = None,
    ) -> tuple[Optional[float], Optional[float]]:
        """Compute Pressure Recovery Time from S3 nadir to SBP returning to baseline.

        t_end caps the search window to avoid artefacts (e.g. Finapres
        mid-recording calibration) inflating PRT beyond physiological limits.
        """
        m = (t > t_s3e) & (t <= t_end) if t_end is not None else (t > t_s3e)
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
