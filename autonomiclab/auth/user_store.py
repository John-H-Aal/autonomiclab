"""Encrypted SQLite store for User records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import bcrypt

from autonomiclab.auth.crypto import decrypt_bytes, encrypt_bytes
from autonomiclab.auth.models import Role, User
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username  TEXT PRIMARY KEY,
    role      TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    blob      TEXT NOT NULL
);
"""


class UserStore:
    """Thread-safe, Fernet-encrypted user database backed by SQLite.

    Sensitive fields are stored as an encrypted JSON blob.  The
    ``username``, ``role``, and ``is_active`` columns are plaintext so
    that simple queries work without decrypting every row.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ── internal helpers ─────────────────────────────────────────────────────

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        con = sqlite3.connect(self._path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def _init_db(self) -> None:
        with self._conn() as con:
            con.executescript(_SCHEMA)

    @staticmethod
    def _user_to_blob(user: User) -> str:
        data = {
            "username":      user.username,
            "display_name":  user.display_name,
            "password_hash": user.password_hash,
            "role":          user.role.value,
            "is_active":     user.is_active,
            "created_at":    user.created_at,
        }
        return encrypt_bytes(json.dumps(data).encode()).decode()

    @staticmethod
    def _blob_to_user(blob: str) -> User:
        data = json.loads(decrypt_bytes(blob.encode()))
        return User(
            username=data["username"],
            display_name=data["display_name"],
            password_hash=data["password_hash"],
            role=Role(data["role"]),
            is_active=bool(data["is_active"]),
            created_at=data["created_at"],
        )

    # ── public API ───────────────────────────────────────────────────────────

    def add_user(self, user: User) -> None:
        blob = self._user_to_blob(user)
        with self._conn() as con:
            con.execute(
                "INSERT INTO users (username, role, is_active, blob) VALUES (?,?,?,?)",
                (user.username, user.role.value, int(user.is_active), blob),
            )
        log.info("User added: %s (%s)", user.username, user.role.value)

    def get_user(self, username: str) -> User | None:
        with self._conn() as con:
            row = con.execute(
                "SELECT blob FROM users WHERE username=?", (username,)
            ).fetchone()
        if not row:
            return None
        try:
            return self._blob_to_user(row["blob"])
        except Exception:
            log.exception("Failed to decrypt user record for %s", username)
            return None

    def update_user(self, user: User) -> None:
        blob = self._user_to_blob(user)
        with self._conn() as con:
            con.execute(
                "UPDATE users SET role=?, is_active=?, blob=? WHERE username=?",
                (user.role.value, int(user.is_active), blob, user.username),
            )
        log.info("User updated: %s", user.username)

    def delete_user(self, username: str) -> None:
        with self._conn() as con:
            con.execute("DELETE FROM users WHERE username=?", (username,))
        log.info("User deleted: %s", username)

    def list_users(self) -> list[User]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT blob FROM users ORDER BY username"
            ).fetchall()
        users = []
        for row in rows:
            try:
                users.append(self._blob_to_user(row["blob"]))
            except Exception:
                log.exception("Skipping corrupt user record")
        return users

    def authenticate(self, username: str, password: str) -> User | None:
        """Return User if credentials are valid and account is active, else None."""
        user = self.get_user(username)
        if not user or not user.is_active:
            return None
        try:
            if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
                return user
        except Exception:
            log.exception("bcrypt check failed for %s", username)
        return None

    def has_any_user(self) -> bool:
        with self._conn() as con:
            count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return count > 0

    # ── password helpers ─────────────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def set_password(self, username: str, new_password: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        user.password_hash = self.hash_password(new_password)
        self.update_user(user)
        return True
