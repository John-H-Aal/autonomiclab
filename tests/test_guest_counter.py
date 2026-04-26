"""Tests for the HMAC-signed guest launch counter."""

import json
import pytest

from autonomiclab.auth.crypto import guest_sign, mac_hash
from autonomiclab.auth.guest_counter import GuestCounterStore


@pytest.fixture
def counter_path(tmp_path):
    return tmp_path / "guest_counter.json"


@pytest.fixture
def store(counter_path):
    return GuestCounterStore(counter_path)


# ── initial state ─────────────────────────────────────────────────────────────

def test_starts_at_ten(store):
    assert store.remaining() == 10


def test_has_launches_initially(store):
    assert store.has_launches()


# ── consume ───────────────────────────────────────────────────────────────────

def test_consume_returns_true_and_decrements(store):
    assert store.consume() is True
    assert store.remaining() == 9


def test_consume_until_zero(store):
    for _ in range(10):
        assert store.consume() is True
    assert store.remaining() == 0
    assert store.has_launches() is False


def test_consume_at_zero_returns_false(store):
    for _ in range(10):
        store.consume()
    assert store.consume() is False
    assert store.remaining() == 0


# ── persistence ───────────────────────────────────────────────────────────────

def test_persists_across_instances(counter_path):
    GuestCounterStore(counter_path).consume()
    assert GuestCounterStore(counter_path).remaining() == 9


# ── tamper detection ──────────────────────────────────────────────────────────

def test_tampered_remaining_resets_to_zero(counter_path):
    """Modifying 'remaining' in the file without updating the signature must
    be detected and the counter reset to 0 (not the tampered value)."""
    mh = mac_hash()
    tampered = {
        "mac_hash":  mh,
        "remaining": 999,
        "sig":       "not-a-valid-hmac",
    }
    counter_path.write_text(json.dumps(tampered))
    assert GuestCounterStore(counter_path).remaining() == 0


def test_valid_signature_accepted(counter_path):
    mh = mac_hash()
    remaining = 7
    valid = {
        "mac_hash":  mh,
        "remaining": remaining,
        "sig":       guest_sign(mh, remaining),
    }
    counter_path.write_text(json.dumps(valid))
    assert GuestCounterStore(counter_path).remaining() == 7
