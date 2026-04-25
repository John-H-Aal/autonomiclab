"""Entry point for AutonomicLab application."""

import logging
import sys
import traceback
from pathlib import Path

from autonomiclab.utils.logger import configure_root_logger


def _log_path() -> Path:
    """Return path to log file next to the exe (installed) or in project root (dev)."""
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — write next to the .exe
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    return base / "autonomiclab.log"


def _install_exception_hook(log: logging.Logger) -> None:
    """Catch any unhandled exception and write it to the log before crashing.

    RuntimeErrors about deleted C++ Qt objects (pyqtgraph stale-pointer bugs)
    are logged as warnings and swallowed — they don't corrupt application state
    and must not take down the process.
    """
    def _hook(exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        if exc_type is RuntimeError and "deleted" in str(exc_value):
            log.warning("Suppressed pyqtgraph stale C++ object error:\n%s", msg)
            return
        log.critical("Unhandled exception:\n%s", msg)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def _find_splash_image() -> Path | None:
    """Locate splash PNG next to exe, in project root, or bundled."""
    candidates = [
        Path(sys.executable).parent / "autonomiclab_splash.png",       # next to .exe
        Path(__file__).parent.parent / "assets" / "autonomiclab_splash.png",  # dev
    ]
    # PyInstaller bundle (_MEIPASS)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / "autonomiclab_splash.png")

    return next((p for p in candidates if p.exists()), None)


def main() -> int:
    log_file = _log_path()
    configure_root_logger(log_file=log_file)

    log = logging.getLogger(__name__)
    log.info("AutonomicLab starting — log: %s", log_file)
    _install_exception_hook(log)

    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWidgets import QApplication, QSplashScreen
    from autonomiclab.gui.main_window import MainWindow

    app = QApplication(sys.argv)

    splash_path = _find_splash_image()
    splash = None
    if splash_path:
        from autonomiclab import __version__
        from PyQt6.QtGui import QPainter, QFont, QColor
        pixmap = QPixmap(str(splash_path))
        painter = QPainter(pixmap)
        font = QFont("Arial", 11)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 200))
        margin = 18
        top = 22
        painter.drawText(
            pixmap.rect().adjusted(0, top, -margin, 0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            f"v{__version__}",
        )
        painter.end()
        splash = QSplashScreen(
            pixmap,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
        )
        splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        splash.show()
        app.processEvents()

    def launch():
        from autonomiclab.config.app_settings import AppSettings
        from autonomiclab.auth.user_store import UserStore
        from autonomiclab.auth.guest_counter import GuestCounterStore
        from autonomiclab.auth.sync import sync_users_db
        from autonomiclab.gui.auth.login_dialog import LoginDialog
        from PyQt6.QtWidgets import QDialog

        settings     = AppSettings()
        db_path      = settings.users_db_path
        counter_path = db_path.parent / "guest_counter.json"

        # Try to pull a fresher users.db from OneDrive (silently skipped offline).
        if settings.users_db_url:
            sync_users_db(settings.users_db_url, db_path)

        store   = UserStore(db_path)
        counter = GuestCounterStore(counter_path)

        # First-run: no users exist yet — go straight in (setup mode).
        if not store.has_any_user():
            log.warning("No users in database — bypassing login (first run)")
        else:
            dlg = LoginDialog(store, counter)
            if splash:
                splash.finish(dlg)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                app.quit()
                return

        window = MainWindow()
        window.show()
        if splash:
            splash.finish(window)

    # Delay main window by 2.5s so splash is clearly visible
    SPLASH_MS = 2500 if splash else 0
    QTimer.singleShot(SPLASH_MS, launch)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
