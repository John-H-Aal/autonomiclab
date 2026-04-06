"""Data models for the auth system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    ADMIN        = "admin"
    INVESTIGATOR = "investigator"
    GUEST        = "guest"


@dataclass
class User:
    username:      str
    display_name:  str
    password_hash: str       # bcrypt hash
    role:          Role
    is_active:     bool = True
    created_at:    str  = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class GuestCounter:
    mac_hash:  str           # SHA-256 of primary MAC address
    remaining: int           # launches remaining
    sig:       str           # HMAC-SHA256 signature
