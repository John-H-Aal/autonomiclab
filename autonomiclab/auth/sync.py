"""Download users.db from a remote URL (OneDrive share) when a newer version exists."""

from __future__ import annotations

import shutil
import tempfile
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_TIMEOUT = 8  # seconds


def sync_users_db(url: str, local_path: Path) -> bool:
    """Download *url* to *local_path* if the remote is newer.

    Returns True if the file was updated, False if already up-to-date or
    if the download failed (the local copy is left untouched in that case).

    The remote server must honour ``If-Modified-Since`` or at least return a
    ``Last-Modified`` header — OneDrive direct-download links do both.
    """
    if not url:
        return False

    headers: dict[str, str] = {}
    if local_path.exists():
        try:
            mtime = local_path.stat().st_mtime
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            headers["If-Modified-Since"] = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
        except Exception:
            pass

    try:
        from urllib.request import Request
        req = Request(url, headers=headers)
        with urlopen(req, timeout=_TIMEOUT) as resp:
            if resp.status == 304:
                log.debug("users.db is up-to-date (304 Not Modified)")
                return False

            # Stream to a temp file, then replace atomically.
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=local_path.parent, delete=False, suffix=".tmp"
            ) as tmp:
                shutil.copyfileobj(resp, tmp)
                tmp_path = Path(tmp.name)

            tmp_path.replace(local_path)

            # Preserve Last-Modified so next check works correctly.
            last_mod = resp.headers.get("Last-Modified")
            if last_mod:
                try:
                    dt = parsedate_to_datetime(last_mod)
                    import os, time as _time
                    ts = dt.timestamp()
                    os.utime(local_path, (ts, ts))
                except Exception:
                    pass

            log.info("users.db synced from remote (%d bytes)", local_path.stat().st_size)
            return True

    except URLError as exc:
        log.warning("users.db sync failed (offline?): %s", exc)
        return False
    except Exception:
        log.exception("Unexpected error during users.db sync")
        return False
