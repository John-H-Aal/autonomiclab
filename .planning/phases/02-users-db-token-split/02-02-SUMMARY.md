---
phase: 02-users-db-token-split
plan: 02
subsystem: ci
tags: [auth, ci, installer, token-split]
dependency_graph:
  requires: []
  provides: [USERS_DB_READ_TOKEN secret reference in release.yml]
  affects: [.github/workflows/release.yml]
tech_stack:
  added: []
  patterns: [GitHub Actions secret reference]
key_files:
  modified:
    - .github/workflows/release.yml
decisions:
  - "USERS_DB_TOKEN secret reference replaced with USERS_DB_READ_TOKEN in release.yml iscc invocation; /DUsersDbToken Inno Setup flag name unchanged"
  - "installer.iss config-write block verified: no users_db_admin_token line present; 7-entry array writes data_folder, users_db_token, allow_guest only"
metrics:
  duration: 5m
  completed: 2026-04-26
---

# Phase 2 Plan 02: CI/Installer Changes Summary

CI build step renamed from combined-scope `USERS_DB_TOKEN` to read-only `USERS_DB_READ_TOKEN`; installer.iss config-write block confirmed clean of admin token.

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Rename USERS_DB_TOKEN to USERS_DB_READ_TOKEN in release.yml | Complete | 266b5e3 |
| 2 | Verify installer.iss has no users_db_admin_token line | Complete (verify-only) | — |

## Decisions Made

- `USERS_DB_READ_TOKEN` is the only token secret reference in the iscc step. The `/DUsersDbToken` Inno Setup define name is unchanged (internal to Inno Setup, not a GitHub secret name).
- `installer.iss` `SetArrayLength(Lines, 7)`: Lines[0..6] confirmed to contain only comment lines, `data_folder`, `users_db_token`, `allow_guest`. No `users_db_admin_token` entry. No edit required.

## Deviations from Plan

None — plan executed exactly as written.

## Pre-Merge Ops Reminder (not automated)

- Create GitHub Actions secret `USERS_DB_READ_TOKEN` with the read-only PAT value before tagging a release.
- Do NOT delete `USERS_DB_TOKEN` until the first release with split tokens is verified working.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-02-04 | `USERS_DB_READ_TOKEN` (read-only PAT) replaces `USERS_DB_TOKEN` (combined-scope) in installer build — AUTH-03 satisfied |
| T-02-05 | Accepted: read-only PAT has no write capability; exposure limited to Contents:read on one private repo |

## Self-Check: PASSED

- `266b5e3` exists in git log
- `.github/workflows/release.yml` contains `USERS_DB_READ_TOKEN` (count: 1) and does not contain bare `"USERS_DB_TOKEN"` (count: 0)
- `installer.iss` contains no `users_db_admin_token` (count: 0)
