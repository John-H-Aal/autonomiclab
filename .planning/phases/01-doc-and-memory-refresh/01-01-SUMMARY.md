---
phase: 01
plan: 01
subsystem: docs
tags: [docs, refresh, github-sync]
requires: []
provides:
  - "CLAUDE.md describes v1.0.31 GitHub-sync auth and correct release artifacts"
  - "BUILDING.md release-artifact list matches release.yml"
  - "INSTALLATION.md Step 4 has correct config.yaml install path"
  - "README.md links to docs/user_guide.md and notes first-run login bypass"
affects: []
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - CLAUDE.md
    - BUILDING.md
    - INSTALLATION.md
    - README.md
decisions:
  - "Current-state-only docs (single combined PAT); Phase 2 will re-edit auth sections when token split ships"
  - "README scope kept minimal: one-line user-guide pointer + one-line first-run note, no auth detail leaks"
  - "INSTALLATION.md path-fix only; admin-token instructions deferred to Phase 2"
metrics:
  duration_seconds: 86
  tasks_completed: 4
  completed: "2026-04-26T20:50:26Z"
requirements_completed: [DOCS-01, DOCS-02, DOCS-03, DOCS-04]
---

# Phase 1 Plan 01: Doc & Memory Refresh Summary

Refreshed four root-level docs to describe v1.0.31 reality (GitHub Contents API sync via `users_db_token`, correct release artifacts `AutonomicLab_Setup_<version>.exe` + `UserGuide-<version>.pdf`, correct install-dir `config.yaml` path, README pointer to `docs/user_guide.md`).

## Tasks

| # | Name                                                          | Commit  | Files            |
| - | ------------------------------------------------------------- | ------- | ---------------- |
| 1 | Rewrite CLAUDE.md Auth + Build/release sections (DOCS-01,-02) | 05f44fc | CLAUDE.md        |
| 2 | Correct BUILDING.md release-artifact list (DOCS-02)           | 122343d | BUILDING.md      |
| 3 | Fix INSTALLATION.md Step 4 config.yaml path (DOCS-03)         | 3227b18 | INSTALLATION.md  |
| 4 | Add `## For users` section + first-run note to README (DOCS-04) | d68e2bd | README.md       |

## Verification (grep evidence)

```
$ grep -i "dropbox\|onedrive\|users_db_url" CLAUDE.md BUILDING.md INSTALLATION.md README.md
(no output, exit 1)

$ grep -q 'users_db_token' CLAUDE.md && grep -q 'John-H-Aal/autonomiclab-users' CLAUDE.md && grep -q 'GitHub Contents API' CLAUDE.md
DOCS-01 OK

$ grep -q 'AutonomicLab_Setup_<version>\.exe' CLAUDE.md BUILDING.md && grep -q 'UserGuide-<version>\.pdf' CLAUDE.md BUILDING.md
DOCS-02 OK

$ grep -q 'AppData.Local.AutonomicLab.config\.yaml' INSTALLATION.md
DOCS-03 OK

$ grep -q '^## For users' README.md && grep -q 'Login is skipped on first run' README.md
DOCS-04 OK

$ git diff --name-only HEAD~4 HEAD
BUILDING.md
CLAUDE.md
INSTALLATION.md
README.md
```

No source code or `.planning/` files modified.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- CLAUDE.md modified — verified (FOUND)
- BUILDING.md modified — verified (FOUND)
- INSTALLATION.md modified — verified (FOUND)
- README.md modified — verified (FOUND)
- Commits 05f44fc, 122343d, 3227b18, d68e2bd — all present in `git log`
