# State

**Project:** AutonomicLab
**Milestone:** v1.1.0 — Token-split + doc refresh
**Initialized:** 2026-04-26
**Last updated:** 2026-04-26

## Current Position

- Project initialized via `/gsd-new-project`. Codebase already mapped under `.planning/codebase/` (v1.0.31 snapshot).
- Phase 1 (Doc & Memory Refresh) context captured — `01-CONTEXT.md` and `01-DISCUSSION-LOG.md` written.
- 0 of 2 phases executed.
- Next action: `/gsd-plan-phase 1`.

## Active Phase

Phase 1 — Doc & Memory Refresh (context gathered, awaiting plan)

## Recent Commits

(see git log; planning artifacts committed at init)

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

## Todos Captured

(none — captured directly into REQUIREMENTS.md)
