"""Sync users.db with a private GitHub repository via the Contents API."""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_TIMEOUT  = 10
_REPO     = "John-H-Aal/autonomiclab-users"
_FILE     = "users.db"
_API_URL  = f"https://api.github.com/repos/{_REPO}/contents/{_FILE}"


def _get_remote(token: str) -> tuple[bytes, str] | None:
    """Return (content_bytes, sha) from GitHub, or None on failure."""
    req = Request(_API_URL, headers={
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
    })
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            data    = json.loads(resp.read())
            content = base64.b64decode(data["content"])
            return content, data["sha"]
    except URLError as exc:
        log.warning("users.db fetch failed (offline?): %s", exc)
        return None
    except Exception:
        log.exception("Unexpected error fetching users.db from GitHub")
        return None


def sync_users_db(token: str, local_path: Path) -> bool:
    """Download users.db from GitHub if it differs from the local copy.

    Returns True if the file was updated, False if already current or on error.
    Leaves the local copy untouched on failure.
    """
    if not token:
        return False

    result = _get_remote(token)
    if result is None:
        return False

    remote_content, _ = result

    if local_path.exists() and local_path.read_bytes() == remote_content:
        log.debug("users.db is up-to-date")
        return False

    local_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=local_path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(remote_content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(local_path)

    log.info("users.db synced from GitHub (%d bytes)", len(remote_content))
    return True


def push_users_db(token: str, local_path: Path) -> bool:
    """Upload the local users.db back to GitHub, replacing the remote copy.

    Returns True on success, False on failure.
    """
    if not token or not local_path.exists():
        return False

    result = _get_remote(token)
    if result is None:
        log.warning("Cannot push users.db: failed to get remote SHA")
        return False

    _, current_sha = result

    body = json.dumps({
        "message": "Update users.db",
        "content": base64.b64encode(local_path.read_bytes()).decode(),
        "sha":     current_sha,
    }).encode()

    req = Request(_API_URL, data=body, method="PUT", headers={
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
        "Content-Type":  "application/json",
    })

    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            json.loads(resp.read())
        log.info("users.db pushed to GitHub (%d bytes)", local_path.stat().st_size)
        return True
    except URLError as exc:
        log.warning("users.db push failed: %s", exc)
        return False
    except Exception:
        log.exception("Unexpected error pushing users.db to GitHub")
        return False
