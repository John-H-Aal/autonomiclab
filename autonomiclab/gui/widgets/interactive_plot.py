"""InteractivePlotWidget — pyqtgraph layout widget with snap-to-trace marker placement."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


class InteractivePlotWidget(pg.GraphicsLayoutWidget):
    """GraphicsLayoutWidget with right-click snap-to-nearest-trace marker placement."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plots: list[pg.PlotItem] = []
        self.all_curves: list[tuple[pg.PlotItem, pg.PlotDataItem]] = []
        self.marker_lines: dict[int, pg.InfiniteLine] = {}
        self.snap_mode: bool = False
        self.marker_callback = None
        self._plot_curves: dict[int, list] = {}

        # Patch scene mouse handler to intercept right-click
        self._original_scene_mouse_press = self.scene().mousePressEvent
        self.scene().mousePressEvent = self._scene_mouse_press

    # ── marker placement ──────────────────────────────────────────────────────

    def _scene_mouse_press(self, ev):
        if not self.snap_mode:
            self._original_scene_mouse_press(ev)
            return

        button = ev.button()
        is_right = button == 2 or (hasattr(button, "name") and button.name == "RightButton")

        if not is_right:
            self._original_scene_mouse_press(ev)
            return

        self._snap_to_trace(ev.scenePos())

    def _snap_to_trace(self, scene_pos) -> None:
        for i, plot in enumerate(self.plots):
            try:
                view_pos = plot.vb.mapSceneToView(scene_pos)
                if not plot.vb.viewRect().contains(view_pos):
                    continue

                closest_x = view_pos.x()
                closest_y = view_pos.y()
                closest_plot = plot
                min_dist = float("inf")

                for curve_plot, curve_item in self.all_curves:
                    try:
                        x_data, y_data = curve_item.getData()
                        if x_data is None or len(x_data) == 0:
                            continue
                        x_data = np.array(x_data)
                        y_data = np.array(y_data)
                        x_diff = np.abs(x_data - view_pos.x())
                        idx = np.argmin(x_diff)
                        if x_diff[idx] >= 20:
                            continue
                        cx, cy = x_data[idx], y_data[idx]
                        sp = curve_plot.vb.mapViewToScene(pg.Point(cx, cy))
                        dx = scene_pos.x() - sp.x()
                        dy = scene_pos.y() - sp.y()
                        dist = (dx * dx + dy * dy) ** 0.5
                        if dist < min_dist:
                            min_dist = dist
                            closest_x = cx
                            closest_y = cy
                            closest_plot = curve_plot
                    except Exception as exc:
                        log.debug("Snap: error checking curve: %s", exc)

                # Remove previous marker line on this plot
                if id(closest_plot) in self.marker_lines:
                    try:
                        closest_plot.removeItem(self.marker_lines[id(closest_plot)])
                    except Exception:
                        pass

                marker_line = pg.InfiniteLine(
                    pos=closest_x, angle=90,
                    pen=pg.mkPen("y", width=2, style=pg.QtCore.Qt.PenStyle.SolidLine),
                )
                closest_plot.addItem(marker_line)
                self.marker_lines[id(closest_plot)] = marker_line

                closest_plot.addItem(pg.ScatterPlotItem(
                    x=[closest_x], y=[closest_y], size=10,
                    pen=pg.mkPen("y", width=2),
                    brush=pg.mkBrush(None), symbol="o",
                ))

                log.info("Marker placed: t=%.1f s, y=%.1f", closest_x, closest_y)

                if self.marker_callback:
                    plot_idx = self.plots.index(closest_plot)
                    self.marker_callback(plot_idx, closest_x, closest_y)
                break

            except Exception as exc:
                log.debug("Snap: error in plot %d: %s", i, exc)

    # ── plot registration ─────────────────────────────────────────────────────

    def add_plot_for_tracking(self, plot: pg.PlotItem) -> None:
        """Register a plot so its curves are included in snap-to-trace."""
        self.plots.append(plot)
        plot_id = id(plot)
        for curve in self._plot_curves.get(plot_id, []):
            self.all_curves.append((plot, curve))
        log.debug("Tracking: %d plots, %d curves", len(self.plots), len(self.all_curves))

    # ── safe clear ────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Remove tracked items from the scene before parent clear().

        pyqtgraph's GraphicsLayoutWidget.clear() deletes the C++ ViewBoxes
        but leaves any standalone scene items (InfiniteLines used as markers)
        with stale parent references. Their boundingRect() then crashes on
        the next paint. Explicitly remove them first to break the chain.
        """
        scene = self.scene()
        for line in list(self.marker_lines.values()):
            try:
                if line.scene() is scene:
                    scene.removeItem(line)
            except Exception:
                pass
        self.marker_lines = {}
        self.plots = []
        self.all_curves = []
        self._plot_curves = {}
        super().clear()
