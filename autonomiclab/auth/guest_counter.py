"""Guest launch counter — MAC-bound, HMAC-signed JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from autonomiclab.auth.crypto import guest_sign, guest_verify, mac_hash
from autonomiclab.auth.models import GuestCounter
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_DEFAULT_LAUNCHES = 10


class GuestCounterStore:
    """Persists and validates the per-machine guest launch counter.

    The counter file lives next to the executable (or project root in dev).
    It is a plain JSON file with a HMAC-SHA256 signature so the user cannot
    simply open it in a text editor and bump the count.
    """

    def __init__(self, counter_path: Path) -> None:
        self._path = counter_path

    # ── load / save ──────────────────────────────────────────────────────────

    def _load(self) -> GuestCounter | None:
        if not self._path.exists():
            return None
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            return GuestCounter(
                mac_hash=data["mac_hash"],
                remaining=int(data["remaining"]),
                sig=data["sig"],
            )
        except Exception:
            log.exception("Failed to read guest counter at %s", self._path)
            return None

    def _save(self, counter: GuestCounter) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "mac_hash":  counter.mac_hash,
                        "remaining": counter.remaining,
                        "sig":       counter.sig,
                    },
                    f,
                )
        except Exception:
            log.exception("Failed to save guest counter")

    # ── public API ───────────────────────────────────────────────────────────

    def get_or_create(self) -> GuestCounter:
        """Return the counter for this machine, creating it if absent."""
        mh = mac_hash()
        counter = self._load()

        if counter is None:
            # First guest use on this machine — create fresh counter.
            counter = GuestCounter(
                mac_hash=mh,
                remaining=_DEFAULT_LAUNCHES,
                sig=guest_sign(mh, _DEFAULT_LAUNCHES),
            )
            self._save(counter)
            log.info("Guest counter created: %d launches", _DEFAULT_LAUNCHES)
            return counter

        # Validate signature and MAC binding.
        if counter.mac_hash != mh:
            log.warning("Guest counter MAC mismatch — resetting")
            counter = GuestCounter(mh, _DEFAULT_LAUNCHES, guest_sign(mh, _DEFAULT_LAUNCHES))
            self._save(counter)
            return counter

        if not guest_verify(counter.mac_hash, counter.remaining, counter.sig):
            log.warning("Guest counter signature invalid — resetting")
            counter = GuestCounter(mh, 0, guest_sign(mh, 0))
            self._save(counter)
            return counter

        return counter

    def remaining(self) -> int:
        return self.get_or_create().remaining

    def consume(self) -> bool:
        """Decrement counter by 1.  Returns True if a launch was available."""
        counter = self.get_or_create()
        if counter.remaining <= 0:
            return False
        counter.remaining -= 1
        counter.sig = guest_sign(counter.mac_hash, counter.remaining)
        self._save(counter)
        log.info("Guest launch consumed — %d remaining", counter.remaining)
        return True

    def has_launches(self) -> bool:
        return self.remaining() > 0
