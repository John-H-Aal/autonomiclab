"""Active session — module-level singleton for the current logged-in user."""

from __future__ import annotations

from autonomiclab.auth.models import Role, User

_current_user: User | None = None


def login(user: User) -> None:
    global _current_user
    _current_user = user


def logout() -> None:
    global _current_user
    _current_user = None


def current_user() -> User | None:
    return _current_user


def is_authenticated() -> bool:
    return _current_user is not None


def is_admin() -> bool:
    return _current_user is not None and _current_user.role == Role.ADMIN


def is_guest() -> bool:
    return _current_user is not None and _current_user.role == Role.GUEST
