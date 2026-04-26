"""Tests for the encrypted user store (auth layer)."""

import pytest

from autonomiclab.auth.models import Role, User
from autonomiclab.auth.user_store import UserStore


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    return UserStore(tmp_path / "test_users.db")


def _user(username="alice", role=Role.INVESTIGATOR, active=True) -> User:
    return User(
        username=username,
        display_name=username.title(),
        password_hash=UserStore.hash_password("secret123"),
        role=role,
        is_active=active,
    )


# ── empty store ───────────────────────────────────────────────────────────────

def test_empty_store_has_no_users(store):
    assert not store.has_any_user()


def test_get_nonexistent_user_returns_none(store):
    assert store.get_user("nobody") is None


# ── add / retrieve ────────────────────────────────────────────────────────────

def test_add_and_retrieve(store):
    store.add_user(_user())
    u = store.get_user("alice")
    assert u is not None
    assert u.username == "alice"
    assert u.role == Role.INVESTIGATOR
    assert u.display_name == "Alice"


def test_has_any_user_after_add(store):
    store.add_user(_user())
    assert store.has_any_user()


def test_list_users(store):
    store.add_user(_user("alice"))
    store.add_user(_user("bob", Role.ADMIN))
    users = store.list_users()
    assert {u.username for u in users} == {"alice", "bob"}


# ── authentication ────────────────────────────────────────────────────────────

def test_correct_password_authenticates(store):
    store.add_user(_user())
    assert store.authenticate("alice", "secret123") is not None


def test_wrong_password_fails(store):
    store.add_user(_user())
    assert store.authenticate("alice", "wrongpassword") is None


def test_nonexistent_user_fails(store):
    assert store.authenticate("nobody", "anything") is None


def test_inactive_user_cannot_authenticate(store):
    store.add_user(_user(active=False))
    assert store.authenticate("alice", "secret123") is None


# ── encryption round-trip ─────────────────────────────────────────────────────

def test_encrypted_roundtrip(tmp_path):
    """Closing and reopening the DB must decrypt correctly."""
    db = tmp_path / "roundtrip.db"
    UserStore(db).add_user(_user())
    u = UserStore(db).get_user("alice")
    assert u is not None
    assert u.display_name == "Alice"
    assert u.role == Role.INVESTIGATOR


# ── mutation ──────────────────────────────────────────────────────────────────

def test_delete_user(store):
    store.add_user(_user())
    store.delete_user("alice")
    assert store.get_user("alice") is None
    assert not store.has_any_user()


def test_set_password(store):
    store.add_user(_user())
    store.set_password("alice", "newpassword")
    assert store.authenticate("alice", "newpassword") is not None
    assert store.authenticate("alice", "secret123") is None


def test_update_role(store):
    store.add_user(_user())
    u = store.get_user("alice")
    u.role = Role.ADMIN
    store.update_user(u)
    assert store.get_user("alice").role == Role.ADMIN
