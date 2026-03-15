"""PyQtGraph plotting for interactive zoom/pan"""

import pyqtgraph as pg
import numpy as np


class GATPlotterPyQtGraph:
    """PyQtGraph-based plotter with mouse zoom/pan"""
    
    @staticmethod
    def create_valsalva_plot(plot_widget, dataset, markers, t_start=50, t_end=350):
        """Create Valsalva plot: BP (top), HR+PAirway (bottom)"""
        plot_widget.clear()
        
        rebap_data = dataset.get('reBAP', {})
        hr_data = dataset.get('HR', {})
        pairway_data = dataset.get('PAirway', {})
        
        if not rebap_data or not hr_data or not pairway_data:
            return
        
        rebap_times = np.array(rebap_data.get('times', []))
        rebap_values = np.array(rebap_data.get('values', []))
        hr_times = np.array(hr_data.get('times', []))
        hr_values = np.array(hr_data.get('values', []))
        pairway_times = np.array(pairway_data.get('times', []))
        pairway_values = np.array(pairway_data.get('values', []))
        
        # Filter to time range
        bp_mask = (rebap_times >= t_start) & (rebap_times <= t_end)
        hr_mask = (hr_times >= t_start) & (hr_times <= t_end)
        pa_mask = (pairway_times >= t_start) & (pairway_times <= t_end)
        
        # Create 2 subplots
        plot1 = plot_widget.addPlot(row=0, col=0, title="Blood Pressure (reBAP)")
        plot2 = plot_widget.addPlot(row=1, col=0, title="Heart Rate + Airway Pressure")
        
        # Link x-axes
        plot2.setXLink(plot1)
        
        # ===== SUBPLOT 1: Blood Pressure =====
        pen_bp = pg.mkPen(color='#440154', width=2)
        plot1.plot(rebap_times[bp_mask], rebap_values[bp_mask], pen=pen_bp)
        plot1.setLabel('left', 'BP', units='mmHg')
        plot1.showGrid(x=True, y=True, alpha=0.3)
        
        # Add BP marker lines
        for marker in markers:
            if t_start <= marker['time'] <= t_end:
                vline = pg.InfiniteLine(pos=marker['time'], angle=90, 
                                       pen=pg.mkPen('r', width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
                plot1.addItem(vline)
        
        # ===== SUBPLOT 2: HR + PAirway =====
        pen_hr = pg.mkPen(color='#8B0000', width=2)
        curve_hr = plot2.plot(hr_times[hr_mask], hr_values[hr_mask], pen=pen_hr)
        
        pen_pa = pg.mkPen(color='#0078d4', width=2)
        curve_pa = plot2.plot(pairway_times[pa_mask], pairway_values[pa_mask], pen=pen_pa)
        
        plot2.setLabel('left', 'HR (bpm) / PAirway (mmHg)')
        plot2.setLabel('bottom', 'Time', units='s')
        plot2.showGrid(x=True, y=True, alpha=0.3)
        
        # Add HR marker lines
        for marker in markers:
            if t_start <= marker['time'] <= t_end:
                vline = pg.InfiniteLine(pos=marker['time'], angle=90,
                                       pen=pg.mkPen('r', width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
                plot2.addItem(vline)
        
        # Set x range for both
        plot1.setXRange(t_start, t_end)
        
        # Add legend
        plot1.addLegend()
        plot2.addLegend()
    
    @staticmethod
    def create_stand_test_plot(plot_widget, dataset, markers, t_start=320, t_end=1020):
        """Create Stand Test plot: BP (top), HR (bottom)"""
        plot_widget.clear()
        
        rebap_data = dataset.get('reBAP', {})
        hr_data = dataset.get('HR', {})
        
        if not rebap_data or not hr_data:
            return
        
        rebap_times = np.array(rebap_data.get('times', []))
        rebap_values = np.array(rebap_data.get('values', []))
        hr_times = np.array(hr_data.get('times', []))
        hr_values = np.array(hr_data.get('values', []))
        
        bp_mask = (rebap_times >= t_start) & (rebap_times <= t_end)
        hr_mask = (hr_times >= t_start) & (hr_times <= t_end)
        
        plot1 = plot_widget.addPlot(row=0, col=0, title="Blood Pressure (reBAP)")
        plot2 = plot_widget.addPlot(row=1, col=0, title="Heart Rate")
        
        plot2.setXLink(plot1)
        
        # BP
        pen_bp = pg.mkPen(color='#440154', width=2)
        plot1.plot(rebap_times[bp_mask], rebap_values[bp_mask], pen=pen_bp)
        plot1.setLabel('left', 'BP', units='mmHg')
        plot1.showGrid(x=True, y=True, alpha=0.3)
        
        for marker in markers:
            if t_start <= marker['time'] <= t_end:
                vline = pg.InfiniteLine(pos=marker['time'], angle=90,
                                       pen=pg.mkPen('r', width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
                plot1.addItem(vline)
        
        # HR
        pen_hr = pg.mkPen(color='#8B0000', width=2)
        plot2.plot(hr_times[hr_mask], hr_values[hr_mask], pen=pen_hr)
        plot2.setLabel('left', 'HR', units='bpm')
        plot2.setLabel('bottom', 'Time', units='s')
        plot2.showGrid(x=True, y=True, alpha=0.3)
        
        for marker in markers:
            if t_start <= marker['time'] <= t_end:
                vline = pg.InfiniteLine(pos=marker['time'], angle=90,
                                       pen=pg.mkPen('r', width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
                plot2.addItem(vline)
        
        plot1.setXRange(t_start, t_end)
    
    @staticmethod
    def create_deep_breathing_plot(plot_widget, dataset, markers, t_start=980, t_end=1450):
        """Create Deep Breathing plot: HR (top), Resp Wave (bottom)"""
        plot_widget.clear()
        
        hr_data = dataset.get('HR', {})
        resp_data = dataset.get('Resp Wave', {})
        
        if not hr_data or not resp_data:
            return
        
        hr_times = np.array(hr_data.get('times', []))
        hr_values = np.array(hr_data.get('values', []))
        resp_times = np.array(resp_data.get('times', []))
        resp_values = np.array(resp_data.get('values', []))
        
        hr_mask = (hr_times >= t_start) & (hr_times <= t_end)
        resp_mask = (resp_times >= t_start) & (resp_times <= t_end)
        
        plot1 = plot_widget.addPlot(row=0, col=0, title="Heart Rate (RSA)")
        plot2 = plot_widget.addPlot(row=1, col=0, title="Respiratory Waveform")
        
        plot2.setXLink(plot1)
        
        # HR
        pen_hr = pg.mkPen(color='#8B0000', width=2)
        plot1.plot(hr_times[hr_mask], hr_values[hr_mask], pen=pen_hr)
        plot1.setLabel('left', 'HR', units='bpm')
        plot1.showGrid(x=True, y=True, alpha=0.3)
        
        for marker in markers:
            if t_start <= marker['time'] <= t_end:
                vline = pg.InfiniteLine(pos=marker['time'], angle=90,
                                       pen=pg.mkPen('r', width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
                plot1.addItem(vline)
        
        # Resp Wave
        pen_resp = pg.mkPen(color='#00008B', width=1.5)
        plot2.plot(resp_times[resp_mask], resp_values[resp_mask], pen=pen_resp)
        plot2.setLabel('left', 'Resp', units='mV')
        plot2.setLabel('bottom', 'Time', units='s')
        plot2.showGrid(x=True, y=True, alpha=0.3)
        
        for marker in markers:
            if t_start <= marker['time'] <= t_end:
                vline = pg.InfiniteLine(pos=marker['time'], angle=90,
                                       pen=pg.mkPen('r', width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
                plot2.addItem(vline)
        
        plot1.setXRange(t_start, t_end)