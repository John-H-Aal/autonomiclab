"""Entry point for AutonomicLab application."""

import sys

from autonomiclab.utils.logger import configure_root_logger


def main() -> int:
    configure_root_logger()

    from PyQt6.QtWidgets import QApplication
    from autonomiclab.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
