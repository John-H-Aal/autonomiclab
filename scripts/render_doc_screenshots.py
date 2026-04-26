"""Render LoginDialog and splash screen as PNGs for the user guide."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from autonomiclab import __version__
from autonomiclab.auth.guest_counter import GuestCounterStore
from autonomiclab.auth.models import Role, User
from autonomiclab.auth.user_store import UserStore
from autonomiclab.gui.auth.admin_panel import AdminPanel, _UserFormDialog
from autonomiclab.gui.auth.login_dialog import LoginDialog


def render_splash(out: Path) -> None:
    src = ROOT / "assets" / "autonomiclab_splash.png"
    pixmap = QPixmap(str(src))
    painter = QPainter(pixmap)
    painter.setFont(QFont("Arial", 11))
    painter.setPen(QColor(255, 255, 255, 200))
    painter.drawText(
        pixmap.rect().adjusted(0, 22, -18, 0),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        f"v{__version__}",
    )
    painter.end()
    pixmap.save(str(out), "PNG")
    print(f"wrote {out}")


def render_login(out: Path) -> None:
    tmp = ROOT / "_tmp_render"
    tmp.mkdir(exist_ok=True)
    store = UserStore(tmp / "users.db")
    counter = GuestCounterStore(tmp / "guest_counter.json")

    dlg = LoginDialog(store, counter, allow_guest=True)
    dlg.show()
    QApplication.processEvents()
    pix = dlg.grab()
    pix.save(str(out), "PNG")
    print(f"wrote {out}")

    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


def render_admin(out: Path) -> None:
    tmp = ROOT / "_tmp_render"
    tmp.mkdir(exist_ok=True)
    store = UserStore(tmp / "users.db")
    store.add_user(User(
        username="johhan", display_name="John Hansen",
        password_hash=UserStore.hash_password("x"), role=Role.ADMIN,
    ))
    store.add_user(User(
        username="john", display_name="John Hansen",
        password_hash=UserStore.hash_password("x"), role=Role.INVESTIGATOR,
    ))

    dlg = AdminPanel(store, db_token="")
    dlg.show()
    QApplication.processEvents()
    pix = dlg.grab()
    pix.save(str(out), "PNG")
    print(f"wrote {out}")

    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


def render_add_user(out: Path) -> None:
    tmp = ROOT / "_tmp_render"
    tmp.mkdir(exist_ok=True)
    store = UserStore(tmp / "users.db")

    dlg = _UserFormDialog(store)
    dlg.show()
    QApplication.processEvents()
    pix = dlg.grab()
    pix.save(str(out), "PNG")
    print(f"wrote {out}")

    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


def main() -> None:
    app = QApplication(sys.argv)
    figs = ROOT / "docs" / "figs"
    figs.mkdir(exist_ok=True)
    render_splash(figs / "splash.png")
    render_login(figs / "login.png")
    render_admin(figs / "admin_panel.png")
    render_add_user(figs / "add_user.png")
    app.quit()


if __name__ == "__main__":
    main()
