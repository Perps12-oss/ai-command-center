# Document Hygiene — Active Plans vs Archive

**Status:** Binding repository governance  
**Applies to:** `docs/plans/`, `docs/archive/`, `docs/audits/`, roadmap markdown  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `docs/governance/PHASE_COMPLETION_RULE.md`

---

## Rule

**`docs/plans/` holds only active or incomplete work.**  
**Completed or superseded plans move to `docs/archive/`.**  
**Code on `origin/main` is the only proof a plan may be archived as COMPLETE.**

Never archive a plan as COMPLETE because a status table, agent report, or stale branch says so.

---

## Classification

| Status | Location | Meaning |
|--------|----------|---------|
| `ACTIVE` | `docs/plans/` | Open work; agents may plan from it |
| `PARTIAL` | `docs/plans/` | Some deliverables on `main`; exit criteria unmet — **keep active** |
| `COMPLETE` | `docs/archive/*_COMPLETE.md` | Exit criteria verified against `origin/main` code + tests |
| `SUPERSEDED` | `docs/archive/*_SUPERSEDED.md` | Replaced by another design; do not implement |
| `STALE` | `docs/archive/*_STALE.md` | Untrustworthy claims; do not plan from |

---

## Archive gate (COMPLETE only)

Before moving a plan to `docs/archive/` as COMPLETE:

1. Check out / inventory **`origin/main` tip** (not a feature branch).
2. Extract exit criteria and named deliverables from the plan.
3. Verify each deliverable exists in **source** (and tests where required).
4. Confirm composition-root wiring when the plan requires a live path (not test-only).
5. Record evidence in `docs/audits/` (paths, SHAs, missing items).
6. Only then move the file and update `docs/plans/README.md`.

If any required deliverable is missing, stubbed, or test-only while the plan requires product wiring → **PARTIAL** — leave in `docs/plans/`.

---

## Archive header (required)

Every archived markdown file must begin with:

```markdown
Status: ARCHIVED
Archive-class: COMPLETE | SUPERSEDED | STALE
Superseded-by: <path or "none — shipped on main">
Main-sha: <commit verified against>
Verified-by: <audit path>
Do-not-plan-from: true
```

---

## Living authorities (never archive)

- `PROJECT_CONSTITUTION_V4.md`
- `docs/UI_CONSTITUTION.md`
- `docs/ARCHITECTURE.md` and current architecture contracts
- Current binding audits (e.g. `docs/audits/REPOSITORY_TRUTH_CANON.md`)
- Active phase / UI roadmaps still driving work

Historical audits may be marked superseded in place or moved to `docs/archive/` with a pointer from `docs/audits/`.

---

## Index maintenance

When archiving:

1. Update `docs/plans/README.md` status table (link to archive path).
2. Leave a one-line stub in `docs/plans/` **only if** external links require it; prefer README pointers.
3. Do not leave contradictory “COMPLETE” matrices in active plans.

---

## Agent rules

| Actor | Must |
|-------|------|
| Devin / implementers | Plan only from `docs/plans/` + constitutions + Canon |
| Cursor / Tom | Refuse COMPLETE archive without `origin/main` code evidence |
| Anyone | Treat `Do-not-plan-from: true` as hard stop |

---

## Related

- `docs/governance/PHASE_COMPLETION_RULE.md` — main is the only truth for phase completion  
- `docs/plans/PHASE_0R_REPOSITORY_TRUTH_RECONCILIATION.md` — active reconciliation milestone  
- `docs/audits/REPOSITORY_TRUTH_CANON.md` — inventory SoT  
- `docs/audits/IMPLEMENTATION_TRUTH_MATRIX.md` — Exists / Wired / Tested  
- `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md` — latest code verification of Phase 5–10 plans  
