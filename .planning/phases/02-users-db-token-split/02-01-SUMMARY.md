---
phase: 02-users-db-token-split
plan: "01"
subsystem: auth
tags: [auth, token-split, admin-panel, app-settings]
dependency_graph:
  requires: []
  provides: [users_db_admin_token property, admin-token wiring, missing-token warning]
  affects: [autonomiclab/config/app_settings.py, autonomiclab/gui/main_window.py, autonomiclab/gui/auth/admin_panel.py]
tech_stack:
  added: []
  patterns: [config.yaml two-layer property pattern]
key_files:
  created: []
  modified:
    - autonomiclab/config/app_settings.py
    - autonomiclab/gui/main_window.py
    - autonomiclab/gui/auth/admin_panel.py
decisions:
  - "users_db_admin_token lives in config.yaml; not written by installer"
  - "Warning fires on every admin panel close when token absent (intentional persistent reminder)"
metrics:
  duration: ~5 min
  completed: 2026-04-26
  tasks: 3
  files: 3
---

# Phase 2 Plan 01: Python Source Changes Summary

Two-token auth split — `AppSettings.users_db_admin_token` property added; `AdminPanel` now receives the admin write PAT instead of the shipped read-only PAT; `done()` warns when no admin token is configured.

## Tasks

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Add users_db_admin_token property | 36ca875 | app_settings.py |
| 2 | Wire users_db_admin_token into AdminPanel | ed93e39 | main_window.py |
| 3 | Add missing-token warning to done() | 2c291f0 | admin_panel.py |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `autonomiclab/config/app_settings.py` — `users_db_admin_token` appears 2 times (property def + _config.get call)
- `autonomiclab/gui/main_window.py` — `users_db_admin_token` appears 1 time; no stale `users_db_token` in `_show_admin_panel`
- `autonomiclab/gui/auth/admin_panel.py` — "Sync not configured" appears 1 time; `super().done(result)` remains after the else block
- Import smoke check: `AppSettings().users_db_admin_token` returns `''` (key absent in dev config.yaml)
- Commits 36ca875, ed93e39, 2c291f0 verified in git log
