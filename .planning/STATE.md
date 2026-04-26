# State

**Project:** AutonomicLab
**Milestone:** v1.1.0 — Token-split + doc refresh
**Initialized:** 2026-04-26
**Last updated:** 2026-04-26

## Current Position

- Project initialized via `/gsd-new-project`. Codebase already mapped under `.planning/codebase/` (v1.0.31 snapshot).
- Phase 1 (Doc & Memory Refresh) context captured and **executed** — plan 01-01 complete; all four DOCS-* requirements satisfied.
- 1 of 2 phases executed.
- Next action: `/gsd-plan-phase 2` (token split).

## Active Phase

Phase 2 — users.db Token Split (02-01 and 02-02 complete; 02-03 pending)

## Recent Commits

- 266b5e3 ci: rename USERS_DB_TOKEN secret to USERS_DB_READ_TOKEN [AUTH-03]
- ed93e39 feat(auth): pass users_db_admin_token to AdminPanel [AUTH-02]
- 36ca875 feat(auth): add users_db_admin_token property to AppSettings [AUTH-04]

## Performance Metrics

| Phase-Plan | Duration | Tasks | Files |
|------------|----------|-------|-------|
| 01-01      | 86 sec   | 4     | 4     |
| 02-01      | —        | 3     | 3     |
| 02-02      | 5m       | 2     | 1     |

## Last Session

- Completed 02-02-PLAN.md (2026-04-26)
- Stopped at: Phase 2 plans 01 and 02 complete; 02-03 (docs) pending.
- Resume file: `.planning/phases/02-users-db-token-split/02-02-SUMMARY.md`

## Open Questions / Risks

- **AUTH-04 storage choice:** keyring vs admin-side `config.yaml` line — defer to Phase 2 discuss.
- **AUTH-05 rotation timing:** must follow at least one verified release with split tokens; coordinate with Astrid before revoking on GitHub.
- **Existing dev-tree `config.yaml`** at the project root contains a real-looking PAT (gitignored, not in repo history). On rotation, this local file's value also becomes invalid — reminder for John, no code change needed.

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-26 | Two-token split over scope-restricted single PAT | Single PAT still ships write capability to every install; same exposure surface |
| 2026-04-26 | Skip /gsd-new-project research phase | Codebase already mapped; problem already analysed inline |
| 2026-04-26 | Phase 1 = docs, Phase 2 = code | Docs gate `CLAUDE.md` correctness for the Phase 2 planner agent |
| 2026-04-26 | Phase 1 docs describe v1.0.31 state only (no Phase 2 forward-refs) | Two clean edits beat one preemptive edit; protects against Phase 2 delay |
| 2026-04-26 | README adds one-line `## For users` link to user_guide.md | README stays dev-focused; user_guide owns user content |
| 2026-04-26 | Drop Python-version edit from DOCS-04 | README "3.9+" already matches setup.py; CI 3.12 is unrelated build detail |
| 2026-04-26 | USERS_DB_TOKEN secret reference replaced with USERS_DB_READ_TOKEN in release.yml; /DUsersDbToken Inno Setup flag name unchanged | Explicit names prevent confusion about PAT scope; /D flag is internal to Inno Setup |
| 2026-04-26 | installer.iss config-write block verified: no users_db_admin_token line | Admin PAT must never appear in installer-generated config.yaml; verified absent (AUTH-03 satisfied) |

## Todos Captured

(none — captured directly into REQUIREMENTS.md)
