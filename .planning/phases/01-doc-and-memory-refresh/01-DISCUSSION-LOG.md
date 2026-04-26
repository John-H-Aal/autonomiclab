# Phase 1 — Discussion Log

**Date:** 2026-04-26
**Mode:** default (single-batch confirmation after recommendations)
**Phase:** 1 — Doc & Memory Refresh

## Gray Areas Presented

User selected: all four (A, B, C, D) plus a deferred standalone question ("Is the design/structure of AutonomicLab sound?" — captured as deferred idea, answered inline outside CONTEXT.md scope).

## Decisions

### A. Forward-reference policy for CLAUDE.md auth + build sections

**Options presented:**
1. Current state only (Recommended) — describe v1.0.31 (single combined PAT). Phase 2 will re-edit when the split ships. Two clean edits, doc never lies.
2. Endstate now — describe v1.1.0 endstate preemptively. One edit total, but CLAUDE.md is wrong until Phase 2 ships.

**Selected:** Current state only.

**Notes:** Matches user's "diagnose root cause, no filler" style and protects against Phase 2 delay/re-scope.

---

### B. README addition scope

**Options presented:**
1. One-line user guide link (Recommended) — 'For end users: see docs/user_guide.md' under a 'For users' heading. Keep README dev-focused otherwise.
2. Brief 'For users' section — 2-4 lines on auth/login behaviour and a link.

**Selected:** One-line link.

**Notes:** README is dev entry point; user_guide.md is user entry point. Don't mix.

---

### C. INSTALLATION.md scope

**Options presented:**
1. Fix wrong path only (Recommended) — correct config.yaml path to `{app}\config.yaml` per installer.iss. Admin-token instructions stay in user_guide.md.
2. Add 'Admins only' pointer — also forward-reference Phase 2.

**Selected:** Fix wrong path only.

**Notes:** Don't pre-write Phase 2 docs.

---

### D. Python version statement

**Resolution during discussion:** README's "Python 3.9+" already matches `setup.py`'s `python_requires=">=3.9"`. CI's 3.12 is a build-pipeline detail; PyInstaller bundles its own Python. Not a contradiction.

**Selected:** Drop from scope (Recommended).

**Notes:** DOCS-04 scope shrinks to user-guide link + first-run login note.

---

## Deferred Ideas

| Idea | Why deferred | Where it goes |
|------|--------------|---------------|
| Standalone "is the design sound" review | Outside Phase 1 (doc fixes only); answered inline this session as a side question | Not formalised — could become `/gsd-explore` or milestone audit later |
| Mention admin-token setup in INSTALLATION.md | Phase 2 deliverable | Phase 2 CONTEXT |
| Document offline-tolerant sync behaviour in user_guide.md | Minor polish, not in scope of this milestone | Future docs polish pass |

## Claude's Discretion (no user decision needed)

- Do not edit `.planning/codebase/*.md` — they're regenerated from live code and are already correct.
- Do not edit `docs/user_guide.md` — verified accurate during planning.
- Do not edit memory file `project_auth.md` — already updated this session.
