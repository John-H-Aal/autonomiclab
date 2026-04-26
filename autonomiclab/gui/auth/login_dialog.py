"""Login dialog — shown before MainWindow on every launch."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from autonomiclab.auth import session
from autonomiclab.auth.guest_counter import GuestCounterStore
from autonomiclab.auth.models import Role, User
from autonomiclab.auth.user_store import UserStore
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_INPUT_STYLE = """
    QLineEdit {
        border: 1px solid #bbb;
        border-radius: 4px;
        padding: 6px 8px;
        font-size: 13px;
        background: white;
    }
    QLineEdit:focus { border-color: #0078d4; }
"""

_BTN_PRIMARY = """
    QPushButton {
        background: #0078d4;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 0;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton:hover   { background: #106ebe; }
    QPushButton:pressed { background: #005a9e; }
    QPushButton:disabled { background: #c8c8c8; color: #888; }
"""

_BTN_SECONDARY = """
    QPushButton {
        background: transparent;
        color: #0078d4;
        border: 1px solid #0078d4;
        border-radius: 4px;
        padding: 8px 0;
        font-size: 13px;
    }
    QPushButton:hover   { background: #e8f0fe; }
    QPushButton:pressed { background: #c7d7f7; }
    QPushButton:disabled { color: #bbb; border-color: #bbb; }
"""


class LoginDialog(QDialog):
    """Modal login dialog.

    Accepted (``QDialog.DialogCode.Accepted``) when:
    - Valid username + password → session logged in as that user.
    - Guest launch button → session logged in as a transient guest user.

    Rejected when the user closes the window without logging in.
    """

    def __init__(self, store: UserStore, guest_counter: GuestCounterStore,
                 parent=None, allow_guest: bool = True) -> None:
        super().__init__(parent)
        self._store = store
        self._guest = guest_counter
        self._allow_guest = allow_guest

        self.setWindowTitle("AutonomicLab — Sign In")
        self.setFixedWidth(360)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        root = QVBoxLayout()
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)
        self.setLayout(root)

        # Title
        title = QLabel("Sign In")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #111;")
        root.addWidget(title)
        root.addSpacing(20)

        # Username
        root.addWidget(self._label("Username"))
        root.addSpacing(4)
        self._username = QLineEdit()
        self._username.setPlaceholderText("your.name")
        self._username.setStyleSheet(_INPUT_STYLE)
        root.addWidget(self._username)
        root.addSpacing(12)

        # Password
        root.addWidget(self._label("Password"))
        root.addSpacing(4)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setStyleSheet(_INPUT_STYLE)
        self._password.returnPressed.connect(self._try_login)
        root.addWidget(self._password)
        root.addSpacing(4)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet("color: #c00; font-size: 11px;")
        self._error_lbl.setWordWrap(True)
        root.addWidget(self._error_lbl)
        root.addSpacing(16)

        # Login button
        self._login_btn = QPushButton("Sign In")
        self._login_btn.setStyleSheet(_BTN_PRIMARY)
        self._login_btn.clicked.connect(self._try_login)
        root.addWidget(self._login_btn)

        remaining = self._guest.remaining()
        if self._allow_guest and remaining > 0:
            root.addSpacing(8)
            self._guest_btn = QPushButton(f"Continue as guest  ({remaining} launches left)")
            self._guest_btn.setStyleSheet(_BTN_SECONDARY)
            self._guest_btn.clicked.connect(self._try_guest)
            root.addWidget(self._guest_btn)
        else:
            self._guest_btn = None

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 12px; color: #444; font-weight: 500;")
        return lbl

    def _try_login(self) -> None:
        username = self._username.text().strip()
        password = self._password.text()
        self._error_lbl.setText("")

        if not username or not password:
            self._error_lbl.setText("Enter username and password.")
            return

        user = self._store.authenticate(username, password)
        if user is None:
            self._error_lbl.setText("Incorrect username or password.")
            self._password.clear()
            self._password.setFocus()
            log.warning("Failed login attempt for user: %s", username)
            return

        session.login(user)
        log.info("User logged in: %s (%s)", user.username, user.role.value)
        self.accept()

    def _try_guest(self) -> None:
        if not self._guest.consume():
            QMessageBox.warning(
                self, "Guest access expired",
                "No more guest launches remaining on this machine.\n"
                "Contact the administrator to create a user account.",
            )
            return

        guest_user = User(
            username="guest",
            display_name="Guest",
            password_hash="",
            role=Role.GUEST,
        )
        session.login(guest_user)
        log.info("Guest login — launches remaining after: %d", self._guest.remaining())
        self.accept()
