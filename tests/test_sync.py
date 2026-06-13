"""Tests for users.db GitHub sync — FR-056.

All network calls are mocked so these tests run offline and in CI.
_get_remote is the network boundary inside sync.py — mocking it is
more reliable than mocking urlopen, which requires matching the full
context-manager protocol used by urllib.
"""

import base64
import json
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from autonomiclab.auth.sync import push_users_db, sync_users_db


# ── FR-056: sync_users_db ─────────────────────────────────────────────────────

def test_sync_skips_when_token_empty(tmp_path):
    """Empty token must skip sync immediately and return False."""
    result = sync_users_db("", tmp_path / "users.db")
    assert result is False


def test_sync_returns_false_on_network_error(tmp_path, monkeypatch):
    """A network failure must be absorbed; sync returns False without crashing."""
    monkeypatch.setattr(
        "autonomiclab.auth.sync._get_remote",
        lambda token: None,
    )
    result = sync_users_db("some_token", tmp_path / "users.db")
    assert result is False


def test_sync_skips_when_already_current(tmp_path, monkeypatch):
    """If remote content matches local, return False (no write needed)."""
    content = b"fake_sqlite_db"
    local = tmp_path / "users.db"
    local.write_bytes(content)

    monkeypatch.setattr(
        "autonomiclab.auth.sync._get_remote",
        lambda token: (content, "sha_abc"),
    )
    result = sync_users_db("token123", local)
    assert result is False
    assert local.read_bytes() == content   # file unchanged


def test_sync_replaces_local_when_remote_differs(tmp_path, monkeypatch):
    """If remote content differs, the local file must be overwritten."""
    old_content = b"old_db_bytes"
    new_content = b"new_db_bytes"
    local = tmp_path / "users.db"
    local.write_bytes(old_content)

    monkeypatch.setattr(
        "autonomiclab.auth.sync._get_remote",
        lambda token: (new_content, "sha_new"),
    )
    result = sync_users_db("token123", local)
    assert result is True
    assert local.read_bytes() == new_content


def test_sync_creates_local_file_when_absent(tmp_path, monkeypatch):
    """If no local file exists, sync must create it with the remote content."""
    content = b"fresh_db"
    local = tmp_path / "users.db"
    assert not local.exists()

    monkeypatch.setattr(
        "autonomiclab.auth.sync._get_remote",
        lambda token: (content, "sha_fresh"),
    )
    result = sync_users_db("token123", local)
    assert result is True
    assert local.read_bytes() == content


# ── push_users_db ─────────────────────────────────────────────────────────────

def test_push_skips_when_token_empty(tmp_path):
    result = push_users_db("", tmp_path / "users.db")
    assert result is False


def test_push_skips_when_file_missing(tmp_path):
    result = push_users_db("some_token", tmp_path / "nonexistent.db")
    assert result is False


def test_push_returns_true_on_success(tmp_path, monkeypatch):
    """A successful push (GET sha + PUT) must return True."""
    local = tmp_path / "users.db"
    local.write_bytes(b"db_content")

    # _get_remote is used for both the GET (fetch SHA) step in push_users_db
    # and is also called by sync_users_db — mock it to return a valid SHA.
    monkeypatch.setattr(
        "autonomiclab.auth.sync._get_remote",
        lambda token: (b"db_content", "current_sha"),
    )

    # The PUT request goes directly via urlopen; wrap it in a minimal context mgr.
    class _FakePutResp:
        def read(self):
            return json.dumps({"content": {}, "commit": {}}).encode()
        def __enter__(self): return self
        def __exit__(self, *_): return False

    monkeypatch.setattr(
        "autonomiclab.auth.sync.urlopen",
        lambda *a, **kw: _FakePutResp(),
    )

    result = push_users_db("token123", local)
    assert result is True
