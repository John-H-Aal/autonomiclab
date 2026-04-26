---
phase: 02-users-db-token-split
plan: "03"
subsystem: auth
tags: [github-pat, sync, two-token-model, documentation]

requires:
  - phase: 02-users-db-token-split
    plan: "01"
    provides: users_db_admin_token property and AdminPanel warning behaviour
  - phase: 02-users-db-token-split
    plan: "02"
    provides: USERS_DB_READ_TOKEN CI secret and installer.iss without admin token
provides:
  - CLAUDE.md auth section describes two-token model (read-only shipped, write admin-manual)
  - user_guide.md admin section instructs on users_db_admin_token setup
  - AUTH-05 rotation checklist captured
affects: [future-auth-changes, onboarding, release-ops]

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - CLAUDE.md
    - docs/user_guide.md

key-decisions:
  - "CLAUDE.md auth section now describes two-token model: read-only PAT shipped, write PAT admin-manual"
  - "user_guide.md admin section adds one-time setup block for users_db_admin_token in config.yaml"

patterns-established: []

requirements-completed:
  - AUTH-05

duration: 8min
completed: 2026-04-26
---

# Phase 2 Plan 03: Doc updates + AUTH-05 rotation checklist Summary

**CLAUDE.md and user_guide.md updated to reflect two-token sync model: read-only PAT shipped in installers, write PAT added manually on admin machines only**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-26T00:00:00Z
- **Completed:** 2026-04-26T00:08:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- CLAUDE.md auth section replaced single-PAT description with two-token model (users_db_token / users_db_admin_token), removed stale USERS_DB_TOKEN reference, named USERS_DB_READ_TOKEN CI secret
- user_guide.md "How the user list is shared" section updated to clarify read-only token on launch; added admin machine setup block with config.yaml example
- AUTH-05 rotation checklist captured in verification block (see below)

## Task Commits

1. **Task 1: Re-edit CLAUDE.md auth section** — `ef9a9c5` (docs)
2. **Task 2: Add admin token setup note to user_guide.md** — `f9f3096` (docs)

## Files Created/Modified

- `CLAUDE.md` — Auth section: two-token model, USERS_DB_READ_TOKEN, users_db_admin_token, removed single-PAT language
- `docs/user_guide.md` — Admin section: read-only token clarified on launch; admin machine setup block added

## Decisions Made

None — followed plan as specified.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## AUTH-05 Rotation Checklist (ops — human-executed post-release)

1. Create fine-grained PAT on GitHub (Settings → Developer settings → Fine-grained tokens):
   - Resource owner: John-H-Aal
   - Repository access: Only `autonomiclab-users`
   - Permissions: Contents = Read
   - Name: autonomiclab-read

2. In the autonomiclab repo Actions settings (Settings → Secrets → Actions):
   - Add secret: `USERS_DB_READ_TOKEN` = <new read-only PAT>
   - Keep `USERS_DB_TOKEN` until the new release is verified

3. Push a version tag to trigger a release build with `USERS_DB_READ_TOKEN`.

4. Install the new release. Verify:
   - `sync_users_db()` works on launch (reads users.db from GitHub)
   - `push_users_db()` returns False / HTTP 403 when using the embedded token (read-only PAT cannot PUT)

5. On the admin machine, add `users_db_admin_token` to config.yaml with the write-capable PAT.
   Verify Admin Panel close pushes successfully.

6. After one verified release cycle:
   - Revoke the old combined-scope PAT on GitHub (Developer settings → Personal access tokens → delete)
   - Delete the `USERS_DB_TOKEN` secret from Actions settings
   - Update the local dev-tree `config.yaml` (gitignored) if it contains the old PAT value

## Next Phase Readiness

Phase 2 complete. All code, CI/installer, and documentation changes are committed. AUTH-05 rotation is a post-release ops step requiring a new version tag and manual PAT management on GitHub.

---
*Phase: 02-users-db-token-split*
*Completed: 2026-04-26*
