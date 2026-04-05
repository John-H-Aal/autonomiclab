"""CycleInteractor — interactive RSA cycle editing for the Deep Breathing plot.

Owns all draggable dot pairs, the scene-level click handler for right-click
delete and double-click insert, and notifies the caller via on_cycle_override
whenever cycles change.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from autonomiclab.analysis.deep_breathing import DeepBreathingResult, RSACycle

_C_INSP   = "#B71C1C"   # dark red  — HR max (inspiration)
_C_EXP    = "#1A237E"   # dark blue — HR min (expiration)
_DashLine = pg.QtCore.Qt.PenStyle.DashLine

_DELETE_RADIUS_S = 2.0   # seconds — how close a right-click must be to a dot
_INSERT_SEARCH_S = 3.0   # seconds — half-window for local-max search on insert
_MIN_SEARCH_S    = 6.0   # seconds — forward window for auto-trough after insert


class CycleInteractor:
    """Manages interactive RSA cycle markers on a Deep Breathing PlotItem.

    Parameters
    ----------
    plot:
        The PlotItem that receives all cycle markers.
    result:
        DeepBreathingResult whose ``cycles`` list is mutated in-place.
    t_hr, v_hr:
        HR signal arrays (already sliced to the analysis window).
    on_cycle_override:
        Called with a ``list[dict]`` of ``{max_t, min_t}`` whenever any
        cycle is added, deleted, or dragged to completion.
    """

    def __init__(
        self,
        plot: pg.PlotItem,
        result: DeepBreathingResult,
        t_hr: np.ndarray,
        v_hr: np.ndarray,
        on_cycle_override: Callable[[list[dict]], None],
    ) -> None:
        self._plot = plot
        self._result = result
        self._t_hr = t_hr
        self._v_hr = v_hr
        self._on_cycle_override = on_cycle_override

        for cycle in result.cycles:
            self._add_dot_pair(cycle)

        # Disable pyqtgraph's built-in right-click menu so we can own it.
        plot.vb.setMenuEnabled(False)

        # Disconnect any handler left by a previous plot() call.
        scene = plot.scene()
        old = getattr(scene, "_db_click_handler", None)
        if old is not None:
            try:
                scene.sigMouseClicked.disconnect(old)
            except Exception:
                pass

        scene.sigMouseClicked.connect(self._on_scene_clicked)
        scene._db_click_handler = self._on_scene_clicked

    # ── private helpers ───────────────────────────────────────────────────────

    def _snap(self, t_req: float) -> tuple[float, float]:
        i = int(np.argmin(np.abs(self._t_hr - t_req)))
        return float(self._t_hr[i]), float(self._v_hr[i])

    def _cycles_as_dicts(self) -> list[dict]:
        return [{"max_t": c.max_t, "min_t": c.min_t} for c in self._result.cycles]

    def _rebuild_and_notify(self) -> None:
        self._on_cycle_override(self._cycles_as_dicts())

    def _add_dot_pair(self, cycle: RSACycle) -> None:
        """Add one draggable max+min pair for *cycle*."""
        plot = self._plot

        max_dot = pg.ScatterPlotItem(
            x=[cycle.max_t], y=[cycle.max_v], size=11, symbol="t",
            pen=pg.mkPen(_C_INSP, width=2), brush=pg.mkBrush(_C_INSP),
        )
        max_line = pg.InfiniteLine(
            pos=cycle.max_t, angle=90, movable=True,
            pen=pg.mkPen(_C_INSP, width=1, style=_DashLine),
            hoverPen=pg.mkPen(_C_INSP, width=2),
        )
        min_dot = pg.ScatterPlotItem(
            x=[cycle.min_t], y=[cycle.min_v], size=11, symbol="t1",
            pen=pg.mkPen(_C_EXP, width=2), brush=pg.mkBrush(_C_EXP),
        )
        min_line = pg.InfiniteLine(
            pos=cycle.min_t, angle=90, movable=True,
            pen=pg.mkPen(_C_EXP, width=1, style=_DashLine),
            hoverPen=pg.mkPen(_C_EXP, width=2),
        )

        for item in (max_dot, max_line, min_dot, min_line):
            plot.addItem(item)

        def _on_max_drag():
            t, v = self._snap(max_line.value())
            max_dot.setData(x=[t], y=[v])

        def _on_max_released():
            t, v = self._snap(max_line.value())
            max_line.setValue(t)
            max_dot.setData(x=[t], y=[v])
            cycle.max_t, cycle.max_v = t, v
            cycle.rsa = cycle.max_v - cycle.min_v
            self._rebuild_and_notify()

        def _on_min_drag():
            t, v = self._snap(min_line.value())
            min_dot.setData(x=[t], y=[v])

        def _on_min_released():
            t, v = self._snap(min_line.value())
            min_line.setValue(t)
            min_dot.setData(x=[t], y=[v])
            cycle.min_t, cycle.min_v = t, v
            cycle.rsa = cycle.max_v - cycle.min_v
            self._rebuild_and_notify()

        max_line.sigDragged.connect(_on_max_drag)
        max_line.sigPositionChangeFinished.connect(_on_max_released)
        min_line.sigDragged.connect(_on_min_drag)
        min_line.sigPositionChangeFinished.connect(_on_min_released)

    # ── scene click handler ───────────────────────────────────────────────────

    def _on_scene_clicked(self, ev) -> None:
        pos = self._plot.vb.mapSceneToView(ev.scenePos())
        t_click = float(pos.x())

        # ── right-click: find nearest dot and offer delete ────────────────────
        if ev.button() == QtCore.Qt.MouseButton.RightButton and not ev.double():
            best_cycle = None
            best_dist  = _DELETE_RADIUS_S
            for c in self._result.cycles:
                for t_pt in (c.max_t, c.min_t):
                    d = abs(t_pt - t_click)
                    if d < best_dist:
                        best_dist  = d
                        best_cycle = c
            if best_cycle is None:
                return
            ev.accept()
            menu = QtWidgets.QMenu()
            act = menu.addAction(f"Delete cycle {best_cycle.cycle}")

            def _delete(checked=False, cyc=best_cycle):
                self._result.cycles = [
                    x for x in self._result.cycles if x.cycle != cyc.cycle
                ]
                for n, x in enumerate(self._result.cycles, start=1):
                    x.cycle = n
                QtCore.QTimer.singleShot(0, self._rebuild_and_notify)

            act.triggered.connect(_delete)
            # Store on scene to prevent GC before exec() runs.
            self._plot.scene()._db_menu = menu
            QtCore.QTimer.singleShot(0, lambda m=menu: m.exec(QtGui.QCursor.pos()))
            return

        # ── double left-click: insert new cycle ───────────────────────────────
        if not ev.double() or ev.button() != QtCore.Qt.MouseButton.LeftButton:
            return

        mask = (
            (self._t_hr >= t_click - _INSERT_SEARCH_S) &
            (self._t_hr <= t_click + _INSERT_SEARCH_S)
        )
        if not np.any(mask):
            return
        t_w, v_w = self._t_hr[mask], self._v_hr[mask]
        i_max = int(np.argmax(v_w))
        new_max_t, new_max_v = float(t_w[i_max]), float(v_w[i_max])

        mask2 = (self._t_hr > new_max_t) & (self._t_hr <= new_max_t + _MIN_SEARCH_S)
        if not np.any(mask2):
            return
        t_w2, v_w2 = self._t_hr[mask2], self._v_hr[mask2]
        i_min = int(np.argmin(v_w2))
        new_min_t, new_min_v = float(t_w2[i_min]), float(v_w2[i_min])

        # Ignore if too close to an existing max
        if any(abs(c.max_t - new_max_t) < 1.0 for c in self._result.cycles):
            return

        new_cycle = RSACycle(
            cycle=len(self._result.cycles) + 1,
            max_t=new_max_t, max_v=new_max_v,
            min_t=new_min_t, min_v=new_min_v,
            rsa=new_max_v - new_min_v,
        )
        self._result.cycles.append(new_cycle)
        self._result.cycles.sort(key=lambda c: c.max_t)
        for n, c in enumerate(self._result.cycles, start=1):
            c.cycle = n
        self._rebuild_and_notify()
