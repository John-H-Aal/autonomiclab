"""Mixin that adds Esc → close to any QWidget subclass."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow


class EscapeCloseMixin:

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def reject(self) -> None:
        self.close()

    def closeEvent(self, event) -> None:
        event.accept()
        if isinstance(self, QMainWindow):
            QApplication.quit()
        else:
            self.deleteLater()
