"""Custom widgets for markers and plots"""
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt

class MarkersTableWidget(QTableWidget):
    def __init__(self, markers=None):
        super().__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Time (s)", "Phase", "Label"])
        
        if markers:
            self.populate_markers(markers)
    
    def populate_markers(self, markers):
        self.setRowCount(len(markers))
        for row, marker in enumerate(markers):
            self.setItem(row, 0, QTableWidgetItem(f"{marker.time:.2f}"))
            self.setItem(row, 1, QTableWidgetItem(marker.phase or "Unknown"))
            self.setItem(row, 2, QTableWidgetItem(marker.label))
