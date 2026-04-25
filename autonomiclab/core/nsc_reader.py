"""Reader for Finapres NOVA .nsc binary files.

Format summary (reverse-engineered):
  .nsc  = ZIP archive containing .nsd data files + Measurement.xml
  X.nsd = uint32 LE, (2N+1) values: [start_tick_0, end_tick_0, ..., end_tick_{N-1}, final_tick]
  Y.nsd = uint16 LE, (2N+1) values: same paired structure, physical_value = raw * 0.01
  Tick unit: 50 µs  (1 tick = 50e-6 s)
  Sample i: time_s = (X[2i] + X[2i+1]) / 2 * 50e-6
            value  = (Y[2i] + Y[2i+1]) / 2 * 0.01  (in signal units)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from autonomiclab.core.models import Signal
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_TICK_S = 50e-6  # seconds per tick

# Y-value scale: physical = MinValue + raw_uint16 * (MaxValue - MinValue) / 32768
# Derived empirically: verified against X-window ground truth for IBI, HR, BP, fiAP.
# MinValue=0 for most channels; fiAP/similar waveforms use MinValue=-MaxValue.
_Y_DENOM = 32768.0

# Gap detection: a sample window longer than N× its expected duration is a gap.
# For Waveforms (≥10 Hz) this catches Physiocal holds; for Trends (<10 Hz)
# only very long pauses (>10 beat intervals, ~10 s at 60 bpm) are flagged.
_GAP_FACTOR = 10  # window > factor × expected_period → gap


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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

                # Deduplicate: prefer the first occurrence if short_name repeats
                if short in self._meta:
                    log.debug("Duplicate short_name '%s', keeping first", short)
                    continue

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
        """Read a Y-axis .nsd as uint16 LE array."""
        data = self._zf.read(self._zip_path(filename))
        # File may have an odd byte at the end (rounding); use floor to uint16 count
        n_u16 = len(data) // 2
        return np.frombuffer(data[:n_u16 * 2], dtype="<u2")

    def _load_channel(
        self, meta: _ChannelMeta
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Load raw data for one channel.

        Returns
        -------
        times  : float64 array, seconds from recording start, length N
        values : float64 array, physical units, length N
        gaps   : bool array, True where sample window is abnormally large, length N
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

        # N = number of samples derived from X (authoritative: 2N+1 uint32)
        N_x = (len(x_raw) - 1) // 2
        # Y should also have 2N+1 uint16; trim to N_x pairs
        N = min(N_x, (len(y_raw) - 1) // 2) if len(y_raw) >= 3 else min(N_x, len(y_raw) // 2)
        if N == 0 or len(x_raw) == 0:
            return np.array([]), np.array([]), np.array([], dtype=bool)

        # Extract paired start/end ticks and values
        x_start = x_raw[0::2][:N].astype(np.float64)  # start ticks
        x_end   = x_raw[1::2][:N].astype(np.float64)  # end ticks
        y_start = y_raw[0::2][:N].astype(np.float64)  # start raw values
        y_end   = y_raw[1::2][:N].astype(np.float64)  # end raw values

        # Center time for each sample (seconds from recording start)
        t0 = x_raw[0] * _TICK_S  # recording start time (usually 0)
        times = (x_start + x_end) / 2.0 * _TICK_S - t0

        # Physical value: MinValue + mean(raw) × (MaxValue - MinValue) / 32768
        y_range = meta.max_value - meta.min_value
        scale = y_range / _Y_DENOM if y_range > 0 else 0.01
        values = meta.min_value + (y_start + y_end) / 2.0 * scale

        # Gap detection: window duration >> expected period.
        # expected_period_ticks = 1 / fs / _TICK_S (e.g. 100 at 200 Hz, 10000 at 2 Hz)
        window_ticks = x_end - x_start
        if meta.sample_rate > 0:
            expected_ticks = 1.0 / meta.sample_rate / _TICK_S
            gap_threshold = max(500.0, expected_ticks * _GAP_FACTOR)
        else:
            gap_threshold = 500.0
        gaps = window_ticks > gap_threshold

        n_gaps = int(gaps.sum())
        if n_gaps:
            log.debug(
                "Channel '%s': %d gap/Physiocal samples (%.1f%% of %d)",
                meta.short_name, n_gaps, 100 * n_gaps / N, N,
            )

        return times, values, gaps
