"""Callback protocols shared across the plotting and GUI layers.

Using ``typing.Protocol`` gives structural subtyping: any callable with the
right signature satisfies the protocol — no explicit inheritance needed.
Violations are caught by static analysers (mypy/pyright) rather than at
runtime.
"""

from __future__ import annotations

from typing import Protocol


class BaselineOverrideCallback(Protocol):
    """Called when the investigator moves the baseline region."""

    def __call__(self, t_start: float, t_end: float) -> None: ...


class PointOverrideCallback(Protocol):
    """Called when the investigator drags a named measurement point."""

    def __call__(self, field: str, new_t: float) -> None: ...


class CycleOverrideCallback(Protocol):
    """Called when RSA cycles are added, deleted, or dragged to completion."""

    def __call__(self, cycles: list[dict]) -> None: ...
