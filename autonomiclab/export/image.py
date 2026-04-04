"""PNG export helpers for pyqtgraph plots."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pyqtgraph as pg

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


class ImageExporter:
    """Export pyqtgraph scenes and individual plot items to PNG."""

    def export_scene(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        output_path: Path,
    ) -> None:
        """Export the full scene of a GraphicsLayoutWidget."""
        try:
            pg.QtWidgets.QApplication.processEvents()
            from pyqtgraph.exporters import ImageExporter as _IE
            exp = _IE(plot_widget.scene())
            exp.export(str(output_path))
            log.info("Scene PNG saved: %s", output_path)
        except Exception as exc:
            log.error("Scene PNG export failed: %s", exc)

    def export_plot(
        self,
        plot_item: pg.PlotItem,
        output_path: Path,
    ) -> None:
        """Export a single PlotItem to PNG."""
        try:
            pg.QtWidgets.QApplication.processEvents()
            from pyqtgraph.exporters import ImageExporter as _IE
            exp = _IE(plot_item)
            exp.export(str(output_path))
            log.info("Plot PNG saved: %s", output_path)
        except Exception as exc:
            log.error("Plot PNG export failed: %s", exc)

    def export_zoomed_scene(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        plots: list[Optional[pg.PlotItem]],
        t_start: float,
        t_end: float,
        output_path: Path,
    ) -> None:
        """Set a zoomed X-range on all plots, export scene, then restore links."""
        active = [p for p in plots if p is not None]
        if not active:
            return

        anchor = active[0]
        # Break x-links temporarily so setXRange takes effect independently
        others = active[1:]
        for p in others:
            p.setXLink(None)
        for p in active:
            p.setXRange(t_start, t_end, padding=0)

        self.export_scene(plot_widget, output_path)

        # Restore x-links
        for p in others:
            p.setXLink(anchor)
