# Phase 2 — CONTEXT

**Phase:** 2 — users.db Token Split
**Captured:** 2026-04-26
**Goal (from ROADMAP.md):** Shipped installers can no longer push `users.db` — only admins with a separate admin PAT can.

## Domain

Code phase. Splits the single combined-scope GitHub PAT into:
- **Read-only PAT** — embedded in every installer via `users_db_token`; used only by `sync_users_db()`
- **Admin write PAT** — added manually to `config.yaml` on admin machines only; used only by `push_users_db()` via Admin Panel close

Also updates `CLAUDE.md` auth section to describe the new two-token model (Phase 1 described current single-PAT state; Phase 2 re-edits to match the shipped reality).

## Canonical Refs

Downstream planner/executor MUST read:

- `/home/john/Projects/Python/AutonomicLab/.planning/REQUIREMENTS.md` — AUTH-01..05 definitions
- `/home/john/Projects/Python/AutonomicLab/.planning/ROADMAP.md` — Phase 2 success criteria
- `/home/john/Projects/Python/AutonomicLab/.planning/phases/02-users-db-token-split/02-CONTEXT.md` — this file (locked decisions)
- `/home/john/Projects/Python/AutonomicLab/autonomiclab/auth/sync.py` — `sync_users_db()` and `push_users_db()` signatures
- `/home/john/Projects/Python/AutonomicLab/autonomiclab/config/app_settings.py` — `AppSettings` two-layer pattern (must replicate for new property)
- `/home/john/Projects/Python/AutonomicLab/autonomiclab/gui/auth/admin_panel.py` — `AdminPanel.__init__`, `AdminPanel.done()`, `_db_token` wiring
- `/home/john/Projects/Python/AutonomicLab/autonomiclab/gui/main_window.py` — `_show_admin_panel()` method (lines ~300-306) — where `db_token=` is passed
- `/home/john/Projects/Python/AutonomicLab/.github/workflows/release.yml` — iscc invocation (lines ~94-101) — secret name change
- `/home/john/Projects/Python/AutonomicLab/installer.iss` — `{#UsersDbToken}` write (line 79), `iscc` /D flag name
- `/home/john/Projects/Python/AutonomicLab/CLAUDE.md` — auth section to re-edit after code ships
- `/home/john/Projects/Python/AutonomicLab/docs/user_guide.md` — admin section — may need minor update for two-token setup

## Prior Decisions Carried Forward

- Config key names already established in REQUIREMENTS.md: `users_db_token` (read-only, unchanged), `users_db_admin_token` (new, write-capable)
- Phase 1 CONTEXT locked "current state only" — Phase 2 re-edits CLAUDE.md to describe two-token model after code ships
- AppSettings design: `config.yaml` = admin-managed layer; `~/.autonomiclab/settings.yaml` = per-user prefs — admin PAT belongs in the admin layer

## Decisions

### A. Admin PAT storage (AUTH-04)

**Decision:** `users_db_admin_token` lives in **`config.yaml`** alongside `users_db_token`. Admins add it manually.

**Rationale:** `config.yaml` is already the admin-managed layer (per `AppSettings` docstring: "admin-managed, lives next to the .exe"). No new code paths, no new dependencies, consistent with existing design. Fits Astrid's single-admin use case.

**Implementation:**
- Add `AppSettings.users_db_admin_token` property: reads `self._config.get("users_db_admin_token") or ""`
- The installer-generated `config.yaml` does NOT write `users_db_admin_token` — admins add it manually after install
- `installer.iss` MUST NOT include a `users_db_admin_token` line in its config-write block

**Example config.yaml on Astrid's machine:**
```yaml
users_db_token: "ghp_READ_ONLY_PAT"       # shipped by installer
users_db_admin_token: "ghp_WRITE_PAT"     # added manually by admin
data_folder: "C:/..."
```

### B. Missing-admin-PAT UX when Admin Panel closes (AUTH-02, UI)

**Decision:** Show a `QMessageBox.warning` when admin token is absent on panel close.

**Rationale:** Silent skip leaves Astrid unaware that her changes weren't synced. Warning is actionable — tells her exactly what config key to add.

**Implementation:** `AdminPanel.done()` adds an `else` branch:
```python
else:
    QMessageBox.warning(
        self, "Sync not configured",
        "Changes saved locally.\n"
        "Add users_db_admin_token to config.yaml to enable GitHub sync."
    )
```

**Note:** Warning fires on every close when admin token is absent. This is intentional — persistent reminder until configured. Not a blocker (does not prevent close).

### C. GitHub Actions secret rename

**Decision:** Create new secret `USERS_DB_READ_TOKEN` (with read-only PAT value), update `release.yml` and `installer.iss`, then delete `USERS_DB_TOKEN` after the new release ships.

**Rationale:** Explicit names prevent future confusion about PAT scope. One-time migration cost is low.

**Implementation:**
- `release.yml` line ~98: `${{ secrets.USERS_DB_TOKEN }}` → `${{ secrets.USERS_DB_READ_TOKEN }}`
- `installer.iss` `/DUsersDbToken` parameter name can stay (it's Inno Setup's internal variable name, not the secret name). Only the GitHub Actions secrets reference changes.
- **Before merging:** Create `USERS_DB_READ_TOKEN` secret in GitHub Actions settings with the read-only PAT value. Do NOT delete `USERS_DB_TOKEN` until the new release is verified working.

## Full Change Map

| File | Change | REQ |
|------|--------|-----|
| `autonomiclab/config/app_settings.py` | Add `users_db_admin_token` property (reads `config.yaml["users_db_admin_token"]`) | AUTH-01, AUTH-02 |
| `autonomiclab/gui/main_window.py` | Pass `db_token=self._settings.users_db_admin_token` to `AdminPanel` | AUTH-02 |
| `autonomiclab/gui/auth/admin_panel.py` | `done()` else-branch: warning when admin token absent | AUTH-02, UI |
| `.github/workflows/release.yml` | `USERS_DB_TOKEN` → `USERS_DB_READ_TOKEN` in iscc invocation | AUTH-03 |
| `installer.iss` | Remove any `users_db_admin_token` line from config-write block (verify it's not there) | AUTH-03 |
| `CLAUDE.md` | Re-edit auth section to describe two-token model | — |
| `docs/user_guide.md` | Admin section: add note that admin machines need `users_db_admin_token` in `config.yaml` | — |

**Ops step (not code — AUTH-05):**
1. Create fine-grained PAT (Contents: read, `autonomiclab-users` only) → add as `USERS_DB_READ_TOKEN` GitHub secret
2. Merge the code changes
3. Tag and release → verify installer-embedded token cannot push (HTTP 403 on PUT)
4. Revoke/delete old `USERS_DB_TOKEN` PAT on GitHub
5. Update dev-tree `config.yaml` (local, gitignored) with new read-only PAT value

## Code Context (reusable patterns)

**AppSettings property pattern** (replicate for `users_db_admin_token`):
```python
@property
def users_db_token(self) -> str:
    """GitHub Personal Access Token for users.db sync. Empty = no sync."""
    return self._config.get("users_db_token") or ""
```

**AdminPanel.done() current push pattern** (extend with else-branch):
```python
def done(self, result: int) -> None:
    """Push users.db to GitHub before closing if a token is configured."""
    if self._db_token:
        from autonomiclab.auth.sync import push_users_db
        from autonomiclab.config.app_settings import AppSettings
        db_path = AppSettings().users_db_path
        if not push_users_db(self._db_token, db_path):
            QMessageBox.warning(self, "Sync failed",
                "Could not sync the user list to GitHub.\nChanges are saved locally.")
    super().done(result)
```

## Scope Constraints

- `sync.py` itself needs **no changes** — it already takes the token as a parameter; callers decide which token to pass
- No new Python dependencies
- No changes to `users.db` schema or encryption
- No changes to `sync_users_db()` — it correctly uses whatever token it's given (already reads-only when given a read-only PAT)

## Deferred Ideas

- In-app PAT prompt / keyring storage — if manually adding to config.yaml proves cumbersome for future admins, but fine for current single-admin use case
- Per-user PATs — out of scope per REQUIREMENTS.md
- Signed users.db blobs — out of scope
