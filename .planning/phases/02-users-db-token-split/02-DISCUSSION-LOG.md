# Phase 2 — Discussion Log

**Date:** 2026-04-26
**Mode:** default (single batch, 3 decisions)
**Phase:** 2 — users.db Token Split

## Gray Areas Presented

Three decisions: admin PAT storage (A), missing-admin-PAT UX (B), CI secret naming (C).

## Decisions

### A. Admin PAT storage (users_db_admin_token)

**Options presented:**
1. `config.yaml` — admin adds manually (Recommended)
2. `~/.autonomiclab/settings.yaml` — in-app prompt, persisted per-user

**Selected:** config.yaml.

**Notes:** Fits the existing two-layer design (config.yaml = admin-managed). No new deps or in-app prompt code. Astrid's single-admin case makes manual config.yaml edit trivial.

---

### B. Missing-admin-PAT UX

**Options presented:**
1. Warning dialog (Recommended) — QMessageBox.warning with exact config key to add
2. Silent skip — same as current empty-token behavior

**Selected:** Warning dialog.

**Notes:** Actionable. Fires on every close when unconfigured — persistent reminder, not a blocker.

---

### C. CI secret naming

**Options presented:**
1. Rename to `USERS_DB_READ_TOKEN` (Recommended) — create new secret, update code, delete old after release
2. Keep `USERS_DB_TOKEN` name, swap value — no code change needed

**Selected:** Rename to `USERS_DB_READ_TOKEN`.

**Notes:** One-time migration cost. Explicit scope name prevents future confusion about what the shipped PAT can do.

---

## Claude's Discretion (no user decision needed)

- `sync.py` needs no code changes — it already receives the token as a parameter
- `installer.iss` internal variable `{#UsersDbToken}` name can stay; only the GitHub Actions secret name changes
- `CLAUDE.md` auth section re-edit deferred to Phase 2 execution (not a Phase 1 forward-ref, but a Phase 2 close task)
- `docs/user_guide.md` admin section needs minor addition — admin machines need `users_db_admin_token` in config.yaml

## Deferred Ideas

| Idea | Disposition |
|------|-------------|
| In-app PAT prompt / keyring storage | Defer — fine for current single-admin use case |
| Per-user PATs | Out of scope per REQUIREMENTS.md |
| Signed users.db blobs (PKI) | Out of scope per REQUIREMENTS.md |
