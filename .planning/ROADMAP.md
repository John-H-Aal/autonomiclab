# Roadmap

**Milestone:** v1.1.0 — Token-split + doc refresh
**Phases:** 2 | **Requirements mapped:** 9 | **Coverage:** 100%

| # | Phase | Goal | Requirements | Plans (est.) | Progress |
|---|-------|------|--------------|--------------|----------|
| 1 | Doc & Memory Refresh | Project docs describe the v1.0.31+ code, not pre-Dropbox-removal behaviour | DOCS-01, DOCS-02, DOCS-03, DOCS-04 | 1 | 1/1 plans complete |
| 2 | users.db Token Split | Shipped installers can no longer push `users.db` — only admins with a separate admin PAT can | AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05 | 3 | 0/3 plans |

---

## Phase 1: Doc & Memory Refresh

**Goal:** Eliminate stale references to Dropbox/OneDrive sync and wrong release artifacts/paths so a new contributor (or a fresh Claude session reading `CLAUDE.md`) gets accurate information.

**Requirements:** DOCS-01, DOCS-02, DOCS-03, DOCS-04

**Success criteria:**
1. `grep -i "dropbox\|onedrive\|users_db_url" CLAUDE.md BUILDING.md INSTALLATION.md README.md` returns zero matches.
2. `CLAUDE.md` Auth section names the GitHub repo, the `users_db_token` config key, and the read-only sync direction on launch.
3. `BUILDING.md` and `CLAUDE.md` release-artifact list matches the actual `softprops/action-gh-release` upload step in `release.yml` (`AutonomicLab_Setup_<version>.exe`, `UserGuide-<version>.pdf`).
4. `INSTALLATION.md` Step 4 config-edit path matches the path `installer.iss` writes config.yaml to.
5. `README.md` links to `docs/user_guide.md`, states the Python version that CI builds against, and notes login is skipped on first run when `users.db` is empty.

**UI hint:** no

---

## Phase 2: users.db Token Split

**Goal:** Make the GitHub PAT shipped in every installer read-only, gate `push_users_db` on a separate admin PAT, and rotate the previously-shipped combined-scope PAT.

**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05

**Plans:**
- [ ] 02-01-PLAN.md — Python source: add users_db_admin_token property, update AdminPanel caller, add missing-token warning
- [ ] 02-02-PLAN.md — CI: rename USERS_DB_TOKEN → USERS_DB_READ_TOKEN in release.yml; verify installer.iss
- [ ] 02-03-PLAN.md — Docs: update CLAUDE.md and user_guide.md for two-token model; AUTH-05 rotation checklist

**Success criteria:**
1. A fresh install of the next release contains a `config.yaml` whose `users_db_token` cannot push to `John-H-Aal/autonomiclab-users` (HTTP 403 on PUT).
2. `sync_users_db()` continues to work for all roles (admin / investigator / guest) on a fresh install.
3. `push_users_db()` returns `False` with a clear log message when the admin PAT is missing; succeeds when the admin PAT is supplied via the new mechanism.
4. Admin Panel close on a configured admin machine still pushes `users.db` to GitHub end-to-end.
5. The previously-distributed combined-scope PAT has been revoked on GitHub and a verification commit (or comment in the rollout note) confirms rotation.

**UI hint:** yes (Admin Panel adds an admin-token configuration affordance)

---

## Dependencies

- Phase 2 depends on Phase 1 only for `CLAUDE.md` auth section being accurate (so the planner agent for Phase 2 reads correct context). Code changes are independent.

## Out of Scope (this milestone)

- Signed `users.db` blobs / verifying signatures on the client
- Server-mediated auth
- Per-user PATs
