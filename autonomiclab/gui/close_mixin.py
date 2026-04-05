"""Mixin that adds Esc → close-with-confirmation to any QWidget subclass."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox


class EscapeCloseMixin:

    _closing = False   # guard against re-entrant closeEvent

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def reject(self) -> None:
        self.close()

    def closeEvent(self, event) -> None:
        if self._closing:
            event.accept()
            return
        event.ignore()
        QTimer.singleShot(0, self._ask_close)

    def _ask_close(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Close window")
        msg.setText("Close this window?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return
        self._closing = True
        if isinstance(self, QMainWindow):
            QApplication.quit()
        else:
            self.hide()
            self.deleteLater()
