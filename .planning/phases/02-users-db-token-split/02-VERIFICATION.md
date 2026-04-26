---
phase: 02-users-db-token-split
verified: 2026-04-26T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
human_verification:
  - test: "Before tagging a release: confirm GitHub Actions secret USERS_DB_READ_TOKEN exists in the autonomiclab repo Actions settings with the read-only PAT value."
    expected: "CI build uses USERS_DB_READ_TOKEN; installer embeds a PAT that can only GET, not PUT, John-H-Aal/autonomiclab-users."
    why_human: "GitHub Actions secret configuration is not verifiable from the local codebase."
  - test: "After one verified release cycle: revoke the old combined-scope PAT on GitHub and delete the USERS_DB_TOKEN Actions secret (AUTH-05 step 6)."
    expected: "No combined-scope PAT in circulation; shipped installers carry only read-only token."
    why_human: "PAT revocation is a GitHub UI ops action; cannot be verified from the codebase."
---

# Phase 2: users.db Token Split Verification Report

**Phase Goal:** Shipped installers can no longer push `users.db` — only admins with a separate admin PAT can.
**Verified:** 2026-04-26
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AppSettings exposes `users_db_admin_token` reading from `self._config` | VERIFIED | `app_settings.py` lines 93-95: property returns `self._config.get("users_db_admin_token") or ""` |
| 2 | MainWindow passes `users_db_admin_token` (not `users_db_token`) to AdminPanel | VERIFIED | `main_window.py` line 306: `db_token=self._settings.users_db_admin_token`; no `users_db_token` in `_show_admin_panel` |
| 3 | AdminPanel.done() warns "Sync not configured" when `_db_token` is empty | VERIFIED | `admin_panel.py` lines 128-133: else branch fires QMessageBox.warning with title "Sync not configured"; `super().done(result)` at line 134 outside the else |
| 4 | release.yml passes `USERS_DB_READ_TOKEN` to iscc; no bare `USERS_DB_TOKEN` reference | VERIFIED | `release.yml` line 96: `$token = "${{ secrets.USERS_DB_READ_TOKEN }}"`. No other `USERS_DB_TOKEN` occurrence in the file. `/DUsersDbToken` Inno Setup flag name unchanged (correct). |
| 5 | installer.iss config-write block contains no `users_db_admin_token` line | VERIFIED | Full `installer.iss` read: `SetArrayLength(Lines, 7)`, Lines[5] = `users_db_token: "{#UsersDbToken}"`, Lines[6] = `allow_guest: true`. No admin token entry. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `autonomiclab/config/app_settings.py` | `users_db_admin_token` property reading `_config` | VERIFIED | Lines 93-95; reads `self._config`, not `self._prefs` |
| `autonomiclab/gui/main_window.py` | AdminPanel instantiation uses admin token | VERIFIED | Line 306: `users_db_admin_token` |
| `autonomiclab/gui/auth/admin_panel.py` | else-branch warning in `done()` | VERIFIED | Lines 128-133; QMessageBox imported at module level (line 8) |
| `.github/workflows/release.yml` | `USERS_DB_READ_TOKEN` secret reference | VERIFIED | Line 96 |
| `installer.iss` | No `users_db_admin_token` in config-write block | VERIFIED | Absent; 7-entry array confirmed |
| `CLAUDE.md` | Two-token model described | VERIFIED | Lines 30-32; both token names present; no Dropbox/OneDrive; no bare `USERS_DB_TOKEN` |
| `docs/user_guide.md` | Admin machine setup block with `users_db_admin_token` | VERIFIED | Lines 206-218; config.yaml example present; "First run" and "Disabling guest access" sections unchanged |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main_window.py` | `AdminPanel.__init__` | `db_token=self._settings.users_db_admin_token` | WIRED | Line 306 exact match |
| `admin_panel.py` done() | `QMessageBox.warning` | else branch when `_db_token` is empty | WIRED | Lines 128-133; QMessageBox available from module-level import |
| `release.yml` iscc step | `/DUsersDbToken` Inno Setup define | `secrets.USERS_DB_READ_TOKEN` | WIRED | Line 96 assigns secret to `$token`; line 98/100 pass `/DUsersDbToken=$token` |

### AUTH-XX Checklist

| Check | Result | Evidence |
|-------|--------|---------|
| **AUTH-01**: `sync_users_db` uses read-only token path — `users_db_admin_token` absent from `sync.py` | PASS | Full `sync.py` (110 lines) read; no `users_db_admin_token` reference anywhere. `sync_users_db()` receives token as parameter — caller (app startup) supplies `users_db_token`; push path is separate. |
| **AUTH-01**: `users_db_token` property exists in `app_settings.py` | PASS | Lines 88-90 |
| **AUTH-01**: `users_db_admin_token` property exists in `app_settings.py` | PASS | Lines 93-95 |
| **AUTH-02**: AdminPanel receives admin token from `main_window.py` | PASS | Line 306: `users_db_admin_token` |
| **AUTH-02**: "Sync not configured" warning when token absent | PASS | `admin_panel.py` lines 128-133 |
| **AUTH-02**: `users_db_token` (read-only) not passed to AdminPanel | PASS | No `users_db_token` in `_show_admin_panel`; only `users_db_admin_token` |
| **AUTH-03**: `USERS_DB_READ_TOKEN` in `release.yml` | PASS | Line 96 |
| **AUTH-03**: Bare `USERS_DB_TOKEN` gone from `release.yml` | PASS | Not present |
| **AUTH-03**: `users_db_admin_token` absent from `installer.iss` | PASS | Confirmed absent |
| **AUTH-04**: `users_db_admin_token` reads from `self._config` (not `self._prefs`) | PASS | `app_settings.py` line 95: `return self._config.get("users_db_admin_token") or ""`; this is the admin config.yaml layer, not written by installer |
| **AUTH-05**: Rotation checklist documented in `02-03-SUMMARY.md` | PASS (ops pending) | `02-03-SUMMARY.md` lines 83-106: 6-step checklist present. Reminder: steps 1-2 (create `USERS_DB_READ_TOKEN` Actions secret) must be completed before tagging a release; step 6 (revoke old PAT) after first verified release. |
| **CLAUDE.md**: `users_db_admin_token` present | PASS | Line 31 |
| **CLAUDE.md**: `users_db_token` present | PASS | Line 31 |
| **CLAUDE.md**: No Dropbox/OneDrive | PASS | Absent |
| **Security**: No `users_db_admin_token:` value assignment in `.github/` or `installer.iss` | PASS | `installer.iss` and `release.yml` read in full; no `users_db_admin_token:` value |

### Anti-Patterns Found

None. No stubs, no TODO/FIXME, no empty implementations in modified files.

### Human Verification Required

#### 1. Create USERS_DB_READ_TOKEN Actions secret before tagging

**Test:** In GitHub repo Settings → Secrets and variables → Actions, confirm `USERS_DB_READ_TOKEN` exists with the read-only PAT value.
**Expected:** CI release build succeeds; installer embeds a PAT scoped to Contents: read only on `John-H-Aal/autonomiclab-users`.
**Why human:** GitHub Actions secrets are not visible in the codebase.

#### 2. AUTH-05: Revoke combined-scope PAT after first verified release

**Test:** After one release built with `USERS_DB_READ_TOKEN` is verified working end-to-end (sync on launch + push from admin panel), delete the old combined-scope PAT on GitHub and the `USERS_DB_TOKEN` Actions secret.
**Expected:** No write-capable token in circulation on any installed copy.
**Why human:** PAT lifecycle management is a GitHub UI ops action.

---

_Verified: 2026-04-26_
_Verifier: Claude (gsd-verifier)_
