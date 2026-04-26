# Requirements

## v1 Requirements

### DOCS — Documentation refresh

- [x] **DOCS-01** — `CLAUDE.md` Auth section describes GitHub Contents API sync via `users_db_token`, not Dropbox/OneDrive or `users_db_url`
- [x] **DOCS-02** — `CLAUDE.md` and `BUILDING.md` release-artifact lists match what `.github/workflows/release.yml` actually uploads (`AutonomicLab_Setup_<version>.exe`, `UserGuide-<version>.pdf`)
- [x] **DOCS-03** — `INSTALLATION.md` Step 4 config.yaml path matches `installer.iss` (`{app}\config.yaml`, not `%LocalAppData%`)
- [x] **DOCS-04** — `README.md` links to `docs/user_guide.md`, states correct Python version (matches CI), and notes the auth/login behaviour on first run

### AUTH — users.db token split

- [ ] **AUTH-01** — `autonomiclab/auth/sync.py:sync_users_db` reads from a fine-grained PAT scoped to **Contents: read** on `John-H-Aal/autonomiclab-users` only
- [ ] **AUTH-02** — `autonomiclab/auth/sync.py:push_users_db` requires a separate admin PAT (e.g. `users_db_admin_token`); refuses to push if absent
- [x] **AUTH-03** — `installer.iss` writes only the read-only PAT into the installed `config.yaml`; the GitHub Actions secret used is `USERS_DB_READ_TOKEN` (the existing `USERS_DB_TOKEN` write-capable secret is no longer embedded)
- [ ] **AUTH-04** — Admin Panel asks for the admin PAT on first push attempt and persists it locally on the admin's machine only (e.g. OS keyring or admin-side `config.yaml` line not present in default installer output)
- [ ] **AUTH-05** — The previously-distributed combined-scope PAT is rotated/revoked on GitHub after at least one release with the split tokens has been verified working

## v2 Requirements

(none for this milestone)

## Out of Scope

- **Signed users.db blobs (PKI)** — admin signs, every client verifies. Long-term answer; defer until token split has shipped and surfaced any UX friction.
- **Server-mediated auth** — would break the offline-tolerant property the field investigators rely on.
- **Per-user write PATs** — admins are a tiny set; one shared admin PAT is sufficient and avoids per-user rotation overhead.
- **Migration of existing user accounts** — no schema change in this milestone; `users.db` payload stays identical.

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| DOCS-01 | Phase 1 | Done (01-01, commit 05f44fc) |
| DOCS-02 | Phase 1 | Done (01-01, commits 05f44fc, 122343d) |
| DOCS-03 | Phase 1 | Done (01-01, commit 3227b18) |
| DOCS-04 | Phase 1 | Done (01-01, commit d68e2bd) |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Done (02-02, commit 266b5e3) |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
