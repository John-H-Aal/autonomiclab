"""Reader for Finapres NOVA .nsc binary files.

Format summary (verified against CSV exports):
  .nsc = ZIP archive containing .nsd data files + Measurement.xml
  X.nsd = uint32 LE, N values: one timestamp per sample
  Y.nsd = uint16 LE, N values: one raw value per sample (same count as X)
  Tick unit: 100 µs  (1 tick = 100e-6 s)
  Sample i: time_s = X[i] * 100e-6
            value  = MinValue + Y[i] * (MaxValue - MinValue) / 32767
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from autonomiclab.core.markers_handler import determine_phase
from autonomiclab.core.models import Marker, Signal
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_TICK_S = 100e-6  # seconds per tick

# Y-value scale: physical = MinValue + raw_uint16 * (MaxValue - MinValue) / 32767
# Verified against CSV exports for fiAP, fiSYS, and all other channels.
_Y_DENOM = 32767.0

# Gap detection: inter-sample interval > N× expected period → gap/Physiocal hold.
_GAP_FACTOR = 10


@dataclass
class _ChannelMeta:
    short_name: str
    long_name: str
    units: str
    signal_type: str   # 'Waveform' | 'Trend'
    sample_rate: float  # nominal Hz from XML
    min_value: float
    max_value: float
    x_file: str        # filename inside the ZIP
    y_file: str


class NscReader:
    """Parse a Finapres NOVA .nsc file and expose its channels as Signal objects.

    Usage::

        reader = NscReader("/path/to/exam.nsc")
        print(reader.channels())          # list of short names
        sig = reader.read("fiAP")         # Signal(times_s, values_mmHg, unit='mmHg')
        mask = reader.gap_mask("fiAP")    # bool array, True where window is a gap/Physiocal
    """

    def __init__(self, nsc_path: str | Path) -> None:
        self._path = Path(nsc_path)
        if not self._path.exists():
            raise FileNotFoundError(self._path)

        self._zf = zipfile.ZipFile(self._path, "r")
        self._meta: dict[str, _ChannelMeta] = {}  # short_name → meta
        self._cache: dict[str, Signal] = {}
        self._gap_cache: dict[str, np.ndarray] = {}
        self._xml_root: Optional[ET.Element] = None
        self._begin_dt: Optional[datetime] = None

        # Detect optional subdirectory prefix inside the ZIP
        # (real .nsc files store everything under e.g. "2026-03-23_09.33.02/")
        self._zip_prefix = self._detect_zip_prefix()

        self._parse_xml()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def channels(self) -> list[str]:
        """Return list of available channel short-names."""
        return list(self._meta.keys())

    def read(self, short_name: str) -> Signal:
        """Return a Signal for *short_name* with times in seconds and physical values.

        Invalid/gap samples (Physiocal hold or acquisition dropout) are set to NaN.
        Raises ``KeyError`` if the channel is not present in the file.
        """
        if short_name not in self._meta:
            raise KeyError(
                f"Channel '{short_name}' not found. Available: {self.channels()}"
            )
        if short_name in self._cache:
            return self._cache[short_name]

        meta = self._meta[short_name]
        times, values, gap_mask = self._load_channel(meta)

        # NaN-fill gap samples
        values = values.copy()
        values[gap_mask] = np.nan

        sig = Signal(short_name, times, values, meta.units)
        self._cache[short_name] = sig
        return sig

    def gap_mask(self, short_name: str) -> np.ndarray:
        """Return a boolean mask (True = gap / Physiocal hold) for *short_name*."""
        if short_name not in self._meta:
            raise KeyError(short_name)
        if short_name in self._gap_cache:
            return self._gap_cache[short_name]
        meta = self._meta[short_name]
        _, _, mask = self._load_channel(meta)
        self._gap_cache[short_name] = mask
        return mask

    def sample_rate(self, short_name: str) -> float:
        """Return the nominal sample rate (Hz) from XML metadata."""
        return self._meta[short_name].sample_rate

    def units(self, short_name: str) -> str:
        """Return the physical units string for *short_name*."""
        return self._meta[short_name].units

    def signal_type(self, short_name: str) -> str:
        """Return 'Waveform' or 'Trend' for *short_name*."""
        return self._meta[short_name].signal_type

    def close(self) -> None:
        self._zf.close()

    def __enter__(self) -> NscReader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def read_markers(self) -> list[Marker]:
        """Return event markers from Measurement.xml, times relative to MeasurementBegin."""
        if self._xml_root is None or self._begin_dt is None:
            return []
        markers_el = self._xml_root.find("Markers")
        if markers_el is None:
            return []
        result = []
        for m in markers_el:
            label = m.get("Label", "").strip()
            time_str = m.get("MarkerTimeAbs", "")
            marker_type = m.get("MarkerType", "")
            visible = m.get("Visible", "True")
            if not label or not time_str:
                continue
            if visible.lower() == "false":
                continue
            if marker_type == "Recording":  # region anchors, not event markers
                continue
            try:
                t = (self._parse_dt(time_str) - self._begin_dt).total_seconds()
            except Exception:
                continue
            result.append(Marker(time=t, label=label, phase=determine_phase(label)))
        return sorted(result, key=lambda mk: mk.time)

    def read_region_markers(self) -> dict[str, tuple[float, float]]:
        """Return phase windows as {name: (t_start, t_end)}.

        Reads GATResults.xml when present, otherwise infers from protocol
        markers in Measurement.xml (first/last marker per protocol phase).
        """
        regions = self._regions_from_gat()
        if regions:
            return regions
        return self._regions_from_markers()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_dt(s: str) -> datetime:
        """Parse a Finapres datetime string to a naive datetime (no timezone)."""
        s = s.strip().rstrip("Z").replace("T", " ")
        if "." in s:
            base, frac = s.rsplit(".", 1)
            s = base + "." + frac.ljust(6, "0")[:6]
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")

    def _regions_from_gat(self) -> dict[str, tuple[float, float]]:
        """Parse Valsalva and Deep Breathing windows from GATResults.xml."""
        try:
            gat_bytes = self._zf.read(self._zip_path("GATResults.xml"))
        except KeyError:
            return {}
        if self._begin_dt is None:
            return {}
        try:
            gat_root = ET.fromstring(gat_bytes)
        except ET.ParseError:
            return {}

        regions: dict[str, tuple[float, float]] = {}
        counters: dict[str, int] = {}

        _EPOCH = datetime(1, 1, 1)  # .NET default "not set" date

        def _to_rel(s: str) -> float:
            dt = self._parse_dt(s)
            return (dt - self._begin_dt).total_seconds()

        tag_to_name = {"Valsalva": "Valsalva", "DeepBreathingTest": "Deep Breathing"}
        for tag, display in tag_to_name.items():
            for el in gat_root.iter(tag):
                r = el.find("Results")
                if r is None:
                    continue
                begin_str = r.get("BeginTime", "")
                end_str   = r.get("EndTime", "")
                if not begin_str or not end_str:
                    continue
                try:
                    begin_dt = self._parse_dt(begin_str)
                    end_dt   = self._parse_dt(end_str)
                except Exception:
                    continue
                if begin_dt.year < 2:  # skip .NET default 0001-01-01
                    continue
                t_start = (begin_dt - self._begin_dt).total_seconds()
                t_end   = (end_dt   - self._begin_dt).total_seconds()
                counters[display] = counters.get(display, 0) + 1
                regions[f"{display} test {counters[display]}"] = (t_start, t_end)

        return regions

    def _regions_from_markers(self) -> dict[str, tuple[float, float]]:
        """Infer region windows from first/last protocol marker per phase."""
        markers = self.read_markers()
        by_phase: dict[str, list[float]] = {}
        for m in markers:
            if m.phase == "Other":
                continue
            by_phase.setdefault(m.phase, []).append(m.time)
        regions: dict[str, tuple[float, float]] = {}
        for phase, times in by_phase.items():
            regions[f"{phase} test 1"] = (min(times), max(times))
        return regions

    def _detect_zip_prefix(self) -> str:
        """Return the subdirectory prefix used inside the ZIP, or '' if flat."""
        names = self._zf.namelist()
        for name in names:
            if name.endswith("Measurement.xml"):
                return name[: -len("Measurement.xml")]
        return ""

    def _zip_path(self, filename: str) -> str:
        """Resolve a bare filename to its full path inside the ZIP."""
        return self._zip_prefix + filename

    def _parse_xml(self) -> None:
        """Parse Measurement.xml and populate self._meta."""
        try:
            xml_bytes = self._zf.read(self._zip_path("Measurement.xml"))
        except KeyError:
            raise ValueError(f"No Measurement.xml found in {self._path}")

        root = ET.fromstring(xml_bytes)
        self._xml_root = root
        self._begin_dt = self._parse_dt(root.findtext("MeasurementBegin", ""))

        for sc in root.iter("SignalContainer"):
            xax = sc.find("XAxis")
            if xax is None:
                continue
            x_file = xax.findtext("DataFile", "")
            if not x_file:
                continue

            model_signals = sc.find("ModelSignals")
            if model_signals is None:
                continue

            for sig in model_signals.iter("Signal"):
                short = sig.findtext("ShortName", "").strip()
                long  = sig.findtext("Name", "").strip()
                y_file = sig.findtext("DataFile", "").strip()
                units  = sig.findtext("Units", "").strip()
                stype  = sig.findtext("Type", "Waveform").strip()
                try:
                    fs = float(sig.findtext("SampleRate", "0") or 0)
                except ValueError:
                    fs = 0.0
                try:
                    vmin = float(sig.findtext("MinValue", "0") or 0)
                except ValueError:
                    vmin = 0.0
                try:
                    vmax = float(sig.findtext("MaxValue", "0") or 0)
                except ValueError:
                    vmax = 0.0

                if not short or not y_file:
                    continue

                # Duplicates: later container wins (Algo_Y ModelFlow over Signal_Y NIBPM).
                if short in self._meta:
                    log.debug("Duplicate short_name '%s', replacing with later container", short)

                self._meta[short] = _ChannelMeta(
                    short_name=short,
                    long_name=long,
                    units=units,
                    signal_type=stype,
                    sample_rate=fs,
                    min_value=vmin,
                    max_value=vmax,
                    x_file=x_file,
                    y_file=y_file,
                )

        log.debug("NscReader: parsed %d channels from %s", len(self._meta), self._path.name)

    def _load_nsd_x(self, filename: str) -> np.ndarray:
        """Read an X-axis .nsd as uint32 LE array."""
        data = self._zf.read(self._zip_path(filename))
        return np.frombuffer(data, dtype="<u4")

    def _load_nsd_y(self, filename: str) -> np.ndarray:
        """Read a Y-axis .nsd as int16 LE array. Sentinel value -32768 = invalid sample."""
        data = self._zf.read(self._zip_path(filename))
        n = len(data) // 2
        return np.frombuffer(data[:n * 2], dtype="<i2")

    def _load_channel(
        self, meta: _ChannelMeta
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Load raw data for one channel.

        Returns
        -------
        times  : float64 array, seconds from recording start, length N
        values : float64 array, physical units, length N
        gaps   : bool array, True where inter-sample gap is abnormally large, length N
        """
        try:
            x_raw = self._load_nsd_x(meta.x_file)
        except KeyError:
            log.warning("X file '%s' not in archive", meta.x_file)
            return np.array([]), np.array([]), np.array([], dtype=bool)

        try:
            y_raw = self._load_nsd_y(meta.y_file)
        except KeyError:
            log.warning("Y file '%s' not in archive", meta.y_file)
            return np.array([]), np.array([]), np.array([], dtype=bool)

        N = min(len(x_raw), len(y_raw))
        if N == 0:
            return np.array([]), np.array([]), np.array([], dtype=bool)

        x = x_raw[:N].astype(np.float64)
        y_int = y_raw[:N]                          # int16, sentinel = -32768
        sentinel_mask = (y_int == -32768)
        y = y_int.astype(np.float64)

        # Do NOT subtract a per-channel t0: beat-detected channels (reSYS etc.)
        # have their first tick offset into the recording, so subtraction would
        # shift them out of alignment with continuous waveforms like reBAP.
        times = x * _TICK_S

        y_range = meta.max_value - meta.min_value
        scale = y_range / _Y_DENOM if y_range > 0 else 0.01
        values = meta.min_value + y * scale
        values[sentinel_mask] = np.nan

        # Gap detection: inter-sample interval >> expected period.
        # expected_period_ticks = 1 / fs / _TICK_S (e.g. 50 at 200 Hz, 5000 at 2 Hz)
        if N > 1 and meta.sample_rate > 0:
            expected_ticks = 1.0 / meta.sample_rate / _TICK_S
            gap_threshold = max(500.0, expected_ticks * _GAP_FACTOR)
            diffs = np.diff(x_raw[:N].astype(np.float64))
            gaps = np.concatenate([[False], diffs > gap_threshold])
        else:
            gaps = np.zeros(N, dtype=bool)

        n_gaps = int(gaps.sum())
        if n_gaps:
            log.debug(
                "Channel '%s': %d gap/Physiocal samples (%.1f%% of %d)",
                meta.short_name, n_gaps, 100 * n_gaps / N, N,
            )

        return times, values, gaps
