"""Mixin that adds Esc → close-with-confirmation to any QWidget subclass."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox


class EscapeCloseMixin:

    _closing = False

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
        msg.setMinimumWidth(380)

        # addButton with roles avoids the platform icon decorations
        # (Ubuntu adds ❌/✓ to StandardButton.No/Yes which looks misleading)
        no_btn  = msg.addButton("No",  QMessageBox.ButtonRole.NoRole)
        yes_btn = msg.addButton("Yes", QMessageBox.ButtonRole.YesRole)
        msg.setDefaultButton(no_btn)

        msg.exec()
        if msg.clickedButton() is not yes_btn:
            return

        self._closing = True
        if isinstance(self, QMainWindow):
            QApplication.quit()
        else:
            self.hide()
            self.deleteLater()
