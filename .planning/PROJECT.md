# AutonomicLab

## What This Is

PyQt6 desktop app for GAT (autonomic nervous system) protocol analysis. Loads Finapres NOVA recordings (.fef CSV folders or .nsc binary files), runs Valsalva / Stand Test / Deep Breathing analyses, and exports Excel + PNG reports.

- Author: Astrid Juhl Terkelsen
- Dev/maintained by: John Hansen
- Dev platform: Linux; deployed: Windows via PyInstaller + Inno Setup
- Released as a tagged Windows installer through GitHub Actions

## Core Value

A clinician (Astrid + investigators) can load a Finapres recording, get protocol-correct analysis plots, and export a results workbook — without losing data integrity to malformed inputs or sync mistakes.

## Current State (entering this milestone)

- v1.0.31 shipped. Codebase mapped under `.planning/codebase/`.
- Auth: encrypted `users.db` synced via private GitHub repo `John-H-Aal/autonomiclab-users` using a single PAT shipped to every installer (Dropbox/OneDrive sync was dropped).
- Documentation drift: `CLAUDE.md`, `BUILDING.md`, `INSTALLATION.md` still describe pre-1.0.31 behaviour (Dropbox sync, wrong release artifact list, wrong config.yaml install path).

## This Milestone

**Goal:** Close the security gap created by shipping a write-capable PAT to every install, and refresh the docs that no longer match the code.

Two phases:
1. **Doc & Memory Refresh** — `CLAUDE.md`, `BUILDING.md`, `INSTALLATION.md`, `README.md` describe what the code actually does in v1.0.31.
2. **users.db Token Split** — read-only PAT shipped in installers, separate admin PAT controls writes; old PAT rotated.

## Requirements

### Validated

- ✓ Finapres `.fef` CSV folder loader with atomic `(t, v)` parsing — existing
- ✓ Finapres `.nsc` binary reader — existing
- ✓ Valsalva / Stand Test / Deep Breathing analyses + plots — existing
- ✓ Excel + PNG export — existing
- ✓ Three-role auth (admin / investigator / guest) with encrypted `users.db` — existing
- ✓ MAC-bound guest launch counter — existing
- ✓ GitHub Contents API sync for `users.db` (replaces Dropbox/OneDrive) — existing
- ✓ Tagged-release pipeline → Windows installer via PyInstaller + Inno Setup — existing
- ✓ User-facing `docs/user_guide.md` rendered to PDF at release time — existing

### Active

- [ ] **DOCS-01** — CLAUDE.md auth section reflects GitHub sync, not Dropbox/OneDrive
- [ ] **DOCS-02** — CLAUDE.md and BUILDING.md release-artifact lists match `release.yml`
- [ ] **DOCS-03** — INSTALLATION.md config.yaml path matches `installer.iss`
- [ ] **DOCS-04** — README.md links to user guide and states correct Python version
- [ ] **AUTH-01** — `sync_users_db()` uses a read-only PAT (no push capability)
- [ ] **AUTH-02** — `push_users_db()` uses a separate admin PAT
- [ ] **AUTH-03** — Installer ships only the read-only PAT in `config.yaml`
- [ ] **AUTH-04** — Admin Panel collects/stores admin PAT independently of `config.yaml`
- [ ] **AUTH-05** — Existing combined PAT rotated/revoked after rollout

### Out of Scope

- Signed-blob `users.db` (admin signs, client verifies) — bigger initiative, requires real key management
- Server-mediated auth — would break offline tolerance, not justified for this user count
- Per-user PATs — admins are the only writers; one shared admin PAT is sufficient

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two-token split (read-only + admin) over write-scope-only PAT | A scope-only fix still ships a write-capable token to every install; same exposure | — Pending |
| Doc fixes as Phase 1 (not embedded in code phase) | Docs gate onboarding/CLAUDE.md guidance; cleaner commit history | — Pending |
| Skip ecosystem research | Codebase already mapped; problem is well-understood | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Out of Scope with reason
2. Requirements validated? → Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Key Decisions

**After each milestone:**
1. Full review of all sections
2. Core Value still the right priority?
3. Audit Out of Scope — reasons still valid?

---
*Last updated: 2026-04-26 after initialization*
