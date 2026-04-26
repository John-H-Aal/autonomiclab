"""Admin panel — user management UI (admin role only)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from autonomiclab.auth.models import Role, User
from autonomiclab.auth.user_store import UserStore
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_BTN = """
    QPushButton {{
        background: {bg};
        color: {fg};
        border: none;
        border-radius: 3px;
        padding: 5px 12px;
        font-size: 12px;
    }}
    QPushButton:hover   {{ background: {hover}; }}
    QPushButton:pressed {{ background: {press}; }}
    QPushButton:disabled {{ background: #ddd; color: #888; }}
"""

_PRIMARY   = _BTN.format(bg="#0078d4", fg="white", hover="#106ebe", press="#005a9e")
_DANGER    = _BTN.format(bg="#d32f2f", fg="white", hover="#c62828", press="#b71c1c")
_SECONDARY = _BTN.format(bg="#f0f0f0", fg="#333",  hover="#e0e0e0", press="#d0d0d0")

_INPUT = """
    QLineEdit {
        border: 1px solid #bbb;
        border-radius: 3px;
        padding: 5px 7px;
        font-size: 12px;
        background: white;
    }
    QLineEdit:focus { border-color: #0078d4; }
"""


class AdminPanel(QDialog):
    """Simple CRUD interface for managing AutonomicLab user accounts."""

    _COLS = ["Username", "Display Name", "Role", "Active"]

    def __init__(self, store: UserStore, parent=None, db_token: str = "") -> None:
        super().__init__(parent)
        self._store    = store
        self._db_token = db_token
        self.setWindowTitle("User Administration")
        self.resize(700, 480)

        root = QVBoxLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        self.setLayout(root)

        # Title
        title = QLabel("User Administration")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        root.addWidget(title)

        # Table
        self._table = QTableWidget(0, len(self._COLS))
        self._table.setHorizontalHeaderLabels(self._COLS)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._add_btn    = QPushButton("Add User")
        self._edit_btn   = QPushButton("Edit")
        self._passwd_btn = QPushButton("Change Password")
        self._toggle_btn = QPushButton("Enable / Disable")
        self._del_btn    = QPushButton("Delete")

        self._add_btn.setStyleSheet(_PRIMARY)
        self._edit_btn.setStyleSheet(_SECONDARY)
        self._passwd_btn.setStyleSheet(_SECONDARY)
        self._toggle_btn.setStyleSheet(_SECONDARY)
        self._del_btn.setStyleSheet(_DANGER)

        self._add_btn.clicked.connect(self._add_user)
        self._edit_btn.clicked.connect(self._edit_user)
        self._passwd_btn.clicked.connect(self._change_password)
        self._toggle_btn.clicked.connect(self._toggle_active)
        self._del_btn.clicked.connect(self._delete_user)

        for btn in (self._add_btn, self._edit_btn, self._passwd_btn,
                    self._toggle_btn, self._del_btn):
            btn_row.addWidget(btn)
        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(_SECONDARY)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        root.addLayout(btn_row)
        self._refresh()

    def done(self, result: int) -> None:
        """Push users.db to GitHub before closing if a token is configured."""
        if self._db_token:
            from autonomiclab.auth.sync import push_users_db
            from autonomiclab.config.app_settings import AppSettings
            db_path = AppSettings().users_db_path
            if not push_users_db(self._db_token, db_path):
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Sync failed",
                    "Could not sync the user list to GitHub.\n"
                    "Changes are saved locally.",
                )
        else:
            dlg = _AdminTokenDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                from autonomiclab.config.app_settings import AppSettings
                settings = AppSettings()
                if settings.set_admin_token(dlg.token):
                    self._db_token = dlg.token
                    from autonomiclab.auth.sync import push_users_db
                    if not push_users_db(self._db_token, settings.users_db_path):
                        QMessageBox.warning(
                            self, "Sync failed",
                            "Token saved. Could not sync to GitHub right now.\n"
                            "Changes are saved locally.",
                        )
                else:
                    QMessageBox.warning(
                        self, "Could not save token",
                        "Failed to write to config.yaml.\nChanges are saved locally.",
                    )
        super().done(result)

    # ── table helpers ────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        users = self._store.list_users()
        self._table.setRowCount(len(users))
        for row, user in enumerate(users):
            self._table.setItem(row, 0, QTableWidgetItem(user.username))
            self._table.setItem(row, 1, QTableWidgetItem(user.display_name))
            self._table.setItem(row, 2, QTableWidgetItem(user.role.value))
            active_txt = "Yes" if user.is_active else "No"
            item = QTableWidgetItem(active_txt)
            item.setForeground(Qt.GlobalColor.darkGreen if user.is_active else Qt.GlobalColor.red)
            self._table.setItem(row, 3, item)

    def _selected_username(self) -> str | None:
        rows = self._table.selectedItems()
        if not rows:
            return None
        return self._table.item(self._table.currentRow(), 0).text()

    # ── actions ──────────────────────────────────────────────────────────────

    def _add_user(self) -> None:
        dlg = _UserFormDialog(self._store, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh()

    def _edit_user(self) -> None:
        username = self._selected_username()
        if not username:
            return
        user = self._store.get_user(username)
        if not user:
            return
        dlg = _UserFormDialog(self._store, existing=user, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh()

    def _change_password(self) -> None:
        username = self._selected_username()
        if not username:
            return
        dlg = _PasswordDialog(username, self._store, parent=self)
        dlg.exec()

    def _toggle_active(self) -> None:
        username = self._selected_username()
        if not username:
            return
        user = self._store.get_user(username)
        if not user:
            return
        user.is_active = not user.is_active
        self._store.update_user(user)
        log.info("User %s is now active=%s", username, user.is_active)
        self._refresh()

    def _delete_user(self) -> None:
        username = self._selected_username()
        if not username:
            return
        answer = QMessageBox.question(
            self, "Delete User",
            f"Are you sure you want to delete <b>{username}</b>?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._store.delete_user(username)
            self._refresh()


# ── sub-dialogs ───────────────────────────────────────────────────────────────

class _UserFormDialog(QDialog):
    """Create or edit a user account."""

    def __init__(self, store: UserStore, existing: User | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self._store    = store
        self._existing = existing
        self.setWindowTitle("Edit User" if existing else "Add User")
        self.setFixedWidth(340)

        root = QVBoxLayout()
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(8)
        self.setLayout(root)

        def row(label: str, widget: QWidget) -> None:
            root.addWidget(QLabel(label))
            root.addWidget(widget)

        self._uname = QLineEdit(existing.username if existing else "")
        self._uname.setStyleSheet(_INPUT)
        self._uname.setEnabled(existing is None)   # username is immutable
        row("Username", self._uname)

        self._display = QLineEdit(existing.display_name if existing else "")
        self._display.setStyleSheet(_INPUT)
        row("Display Name", self._display)

        self._role_cb = QComboBox()
        for r in Role:
            self._role_cb.addItem(r.value, r)
        if existing:
            idx = self._role_cb.findData(existing.role)
            if idx >= 0:
                self._role_cb.setCurrentIndex(idx)
        row("Role", self._role_cb)

        if existing is None:
            self._pw1 = QLineEdit()
            self._pw1.setEchoMode(QLineEdit.EchoMode.Password)
            self._pw1.setStyleSheet(_INPUT)
            row("Password", self._pw1)

            self._pw2 = QLineEdit()
            self._pw2.setEchoMode(QLineEdit.EchoMode.Password)
            self._pw2.setStyleSheet(_INPUT)
            row("Repeat Password", self._pw2)
        else:
            self._pw1 = self._pw2 = None  # type: ignore[assignment]

        self._error = QLabel("")
        self._error.setStyleSheet("color: #c00; font-size: 11px;")
        root.addWidget(self._error)

        btns = QHBoxLayout()
        ok = QPushButton("Save")
        ok.setStyleSheet(_PRIMARY)
        ok.clicked.connect(self._save)
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(_SECONDARY)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        root.addLayout(btns)

    def _save(self) -> None:
        username = self._uname.text().strip()
        display  = self._display.text().strip()
        role     = self._role_cb.currentData()

        if not username or not display:
            self._error.setText("Fill in all fields.")
            return

        if self._existing is None:
            pw1 = self._pw1.text()
            pw2 = self._pw2.text()
            if not pw1:
                self._error.setText("Enter a password.")
                return
            if pw1 != pw2:
                self._error.setText("Passwords do not match.")
                return
            if self._store.get_user(username):
                self._error.setText("Username is already in use.")
                return
            user = User(
                username=username,
                display_name=display,
                password_hash=UserStore.hash_password(pw1),
                role=role,
            )
            self._store.add_user(user)
        else:
            user = self._existing
            user.display_name = display
            user.role = role
            self._store.update_user(user)

        self.accept()


class _PasswordDialog(QDialog):
    def __init__(self, username: str, store: UserStore, parent=None) -> None:
        super().__init__(parent)
        self._username = username
        self._store    = store
        self.setWindowTitle(f"Change Password — {username}")
        self.setFixedWidth(300)

        root = QVBoxLayout()
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(8)
        self.setLayout(root)

        root.addWidget(QLabel("New Password"))
        self._pw1 = QLineEdit()
        self._pw1.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw1.setStyleSheet(_INPUT)
        root.addWidget(self._pw1)

        root.addWidget(QLabel("Repeat Password"))
        self._pw2 = QLineEdit()
        self._pw2.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw2.setStyleSheet(_INPUT)
        root.addWidget(self._pw2)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #c00; font-size: 11px;")
        root.addWidget(self._error)

        btns = QHBoxLayout()
        ok = QPushButton("Save")
        ok.setStyleSheet(_PRIMARY)
        ok.clicked.connect(self._save)
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(_SECONDARY)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        root.addLayout(btns)

    def _save(self) -> None:
        pw1 = self._pw1.text()
        pw2 = self._pw2.text()
        if not pw1:
            self._error.setText("Enter a password.")
            return
        if pw1 != pw2:
            self._error.setText("Passwords do not match.")
            return
        self._store.set_password(self._username, pw1)
        log.info("Password changed for user: %s", self._username)
        QMessageBox.information(self, "Saved", "Password has been changed.")
        self.accept()


class _AdminTokenDialog(QDialog):
    """One-time dialog to configure the admin GitHub sync token."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure admin sync")
        self.setFixedWidth(440)

        root = QVBoxLayout()
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(8)
        self.setLayout(root)

        root.addWidget(QLabel(
            "Enter your admin GitHub token to sync user changes to GitHub.\n"
            "The token will be saved to config.yaml on this machine."
        ))

        token_row = QHBoxLayout()
        self._token = QLineEdit()
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        self._token.setStyleSheet(_INPUT)
        self._token.setPlaceholderText("github_pat_...")
        token_row.addWidget(self._token)

        show_btn = QPushButton("👁")
        show_btn.setFixedWidth(32)
        show_btn.setCheckable(True)
        show_btn.setStyleSheet(_SECONDARY)
        show_btn.toggled.connect(lambda on: self._token.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
        ))
        token_row.addWidget(show_btn)
        root.addLayout(token_row)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #c00; font-size: 11px;")
        root.addWidget(self._error)

        btns = QHBoxLayout()
        ok = QPushButton("Configure")
        ok.setStyleSheet(_PRIMARY)
        ok.clicked.connect(self._save)
        skip = QPushButton("Skip")
        skip.setStyleSheet(_SECONDARY)
        skip.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(skip)
        root.addLayout(btns)

    def _save(self) -> None:
        token = self._token.text().strip()
        if not token:
            self._error.setText("Enter a token.")
            return
        if not token.startswith("github_"):
            self._error.setText("Token should start with 'github_'.")
            return
        self.accept()

    @property
    def token(self) -> str:
        return self._token.text().strip()
