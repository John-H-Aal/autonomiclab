"""Entry point for AutonomicLab application."""

import sys
from pathlib import Path

from autonomiclab.utils.logger import configure_root_logger


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
    configure_root_logger()

    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWidgets import QApplication, QSplashScreen
    from autonomiclab.gui.main_window import MainWindow

    app = QApplication(sys.argv)

    splash_path = _find_splash_image()
    splash = None
    if splash_path:
        from autonomiclab import __version__
        pixmap = QPixmap(str(splash_path))
        splash = QSplashScreen(
            pixmap,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
        )
        splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        splash.show()
        splash.showMessage(
            f"v{__version__}",
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            Qt.GlobalColor.white,
        )
        app.processEvents()

    def launch():
        window = MainWindow()
        window.show()
        if splash:
            splash.finish(window)

        # Close PyInstaller splash
        try:
            import pyi_splash  # type: ignore
            pyi_splash.close()
        except ImportError:
            pass

    # Delay main window by 2.5s so splash is clearly visible
    SPLASH_MS = 2500 if splash else 0
    QTimer.singleShot(SPLASH_MS, launch)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
