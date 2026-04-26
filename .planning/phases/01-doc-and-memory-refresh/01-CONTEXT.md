# Phase 1 — CONTEXT

**Phase:** 1 — Doc & Memory Refresh
**Captured:** 2026-04-26
**Goal (from ROADMAP.md):** Project docs describe the v1.0.31+ code, not pre-Dropbox-removal behaviour.

## Domain

Pure documentation pass. No source code changes. Targets:

- `CLAUDE.md` — auth section + build/release section
- `BUILDING.md` — release artifacts list
- `INSTALLATION.md` — config.yaml install path
- `README.md` — link to `docs/user_guide.md`, first-run login note

User-facing `docs/user_guide.md` is **already accurate** (verified during planning) — no edit needed.

## Canonical Refs

Downstream researcher / planner / executor MUST read:

- `.planning/PROJECT.md` — milestone scope
- `.planning/REQUIREMENTS.md` — DOCS-01..04 IDs and acceptance language
- `.planning/codebase/INTEGRATIONS.md` — current GitHub-sync facts (auth section)
- `.github/workflows/release.yml` — actual release artifact upload step (lines 103-108)
- `installer.iss` — actual config.yaml install path (lines 43-81)
- `autonomiclab/auth/sync.py` — `users_db_token` config key, sync direction
- `docs/user_guide.md` — already-correct narrative for users.db sync (mirror its tone, do not contradict)

No external ADRs / SPECs exist for this project.

## Prior Decisions Carried Forward

- Memory file `~/.claude/projects/.../memory/project_auth.md` already updated to GitHub-sync model — no further memory edits in this phase.
- `.planning/codebase/INTEGRATIONS.md` already correct (mappers read live code, not the stale CLAUDE.md). Treat it as the source of truth for auth/sync facts when rewriting `CLAUDE.md`.

## Decisions

### A. Forward-reference policy
**Decision:** Describe **current v1.0.31 state only** (single combined PAT). Phase 2 will re-edit the same sections when the token split ships.

**Rationale:** Two clean edits beat one preemptive edit that lies about not-yet-shipped behaviour. If Phase 2 is delayed or re-scoped, current-state docs stay correct. Matches user's "diagnose root cause, no filler" style.

**Implication:** `CLAUDE.md` Auth section says "single GitHub PAT in `users_db_token`" — does NOT mention read/admin split. Same for any auth-related lines elsewhere.

### B. README scope
**Decision:** **One-line user-guide link** under a new "For users" heading. README stays developer-focused otherwise.

**Rationale:** README is the dev entry point; `docs/user_guide.md` is the user entry point. Mixing them muddies both. A single pointer is enough; investigators who land on README at all are likely devs scoping the project.

**Implication:** Add a `## For users` section above `## For developers` with one line: "End-user docs: see [docs/user_guide.md](docs/user_guide.md)." No mention of auth/login behaviour in README itself.

### C. INSTALLATION.md scope
**Decision:** **Fix wrong path only.** Update config.yaml location to match `installer.iss` (`{app}\config.yaml`, i.e. the install dir — typically `C:\Program Files\AutonomicLab\config.yaml` for system-wide install or the per-user equivalent).

**Rationale:** Admin-token setup is a Phase 2 deliverable that already lives in `user_guide.md`'s admin section. Don't pre-write Phase 2 docs in Phase 1.

**Implication:** Step 4 of INSTALLATION.md gets the correct path. Nothing else changes.

### D. Python version (resolved during discussion, not a phase-1 edit)
**Decision:** **No README change.** README's "Python 3.9+" already matches `setup.py`'s `python_requires=">=3.9"`. CI's choice of 3.12 is a build-pipeline detail; PyInstaller bundles its own Python so end users need none.

**Implication:** DOCS-04 scope shrinks to: link to user_guide + first-run login note only. No Python-version line is touched.

## DOCS-XX Final Scope (after this discussion)

| REQ | What changes |
|-----|--------------|
| DOCS-01 | `CLAUDE.md:27-31` Auth section rewritten — GitHub Contents API, `users_db_token`, `John-H-Aal/autonomiclab-users`, "single PAT shipped in installer" (current state only — see Decision A) |
| DOCS-02 | `CLAUDE.md:43` and `BUILDING.md:29-32` release-artifact list updated — actual artifacts are `AutonomicLab_Setup_<version>.exe` + `UserGuide-<version>.pdf` (per `release.yml:106-108`). Config and splash are bundled into the installer, not standalone artifacts |
| DOCS-03 | `INSTALLATION.md:30-32` Step 4 path corrected to `{app}\config.yaml` (matches `installer.iss`) |
| DOCS-04 | `README.md` adds a `## For users` section above `## For developers` with one-line link to `docs/user_guide.md`. Also add a one-line note in the dev section: "Login is skipped on first run when `users.db` is empty — see `docs/user_guide.md` for the admin seeding flow." |

## Code Context (no source changes, but for orientation)

- `autonomiclab/auth/sync.py` — `_REPO = "John-H-Aal/autonomiclab-users"`, `_FILE = "users.db"`, uses GitHub Contents API; PAT comes from `AppSettings.users_db_token`.
- `autonomiclab/config/app_settings.py:88-95` — `users_db_token` and `allow_guest` properties read from `config.yaml`.
- `installer.iss:79` — `users_db_token: "{#UsersDbToken}"` injected at install time from CI secret.
- `.github/workflows/release.yml:103-108` — `softprops/action-gh-release@v2` uploads `dist/AutonomicLab_Setup_*.exe` and `dist/UserGuide-${{ github.ref_name }}.pdf`.

## Deferred Ideas (not for this phase)

- **Standalone design/structure review** (raised by user during gray-area selection) — separate inquiry, answered inline this session, not part of any phase. If formalised later, treat as a `/gsd-explore` or its own milestone audit.
- **Mention admin-token setup in INSTALLATION.md** — defer to Phase 2 doc updates.
- **Document the offline-tolerant sync behaviour** in `user_guide.md` — minor, defer to a future docs polish pass.

## Out of Scope

- Source code changes (those are Phase 2)
- `docs/user_guide.md` edits — already accurate
- `.planning/codebase/*.md` — already accurate, regenerated from live code
- `pyproject.toml` creation — separate concern
