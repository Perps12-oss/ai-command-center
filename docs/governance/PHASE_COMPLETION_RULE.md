# Phase Completion Rule — Main Is the Only Truth

**Status:** Binding repository governance  
**Applies to:** All roadmap phases (Phase 11 onward; retroactively for audits)  
**Authority:** `PROJECT_CONSTITUTION_V4.md` (implementation may not redefine verification)

---

## Rule

**NO phase may be declared complete unless:**

1. **All phase features exist on `main`.**
2. **All phase audits exist on `main`.**
3. **All constitution updates for the phase exist on `main`.**
4. **No active branch contains phase functionality absent from `main`.**

Until those four conditions hold, maximum honest status is `PARTIALLY_IMPLEMENTED` (or lower).

---

## Definitions

| Term | Meaning |
|------|---------|
| Phase features | Workspaces, panels, tokens, verifiers, tests named in the approved phase plan |
| Phase audits | Tom / remediation / primitive-reuse / placeholder (or equivalent) audit artifacts for that phase |
| Constitution updates | `PROJECT_CONSTITUTION_V4.md`, `docs/UI_CONSTITUTION.md`, and phase plan docs that encode acceptance |
| Active branch | Any non-deleted local or remote branch that is not fully superseded and deleted |

Squash merges count as “on `main`” only for **content actually present** in the squash commit — not for later tip commits that never landed.

---

## Enforcement

| Gate | Expectation |
|------|-------------|
| Agents | `.cursor/rules/phase-complete-on-main.mdc` — do not claim COMPLETE off-main |
| Humans / PRs | PR description must state what remains off-main |
| Tom audits | Must inventory `origin/main` vs active branches before COMPLIANT |

---

## Remediation pattern

When phase work is split across branches (the “11E/11F situation”):

1. Create `phase-<N>-final-integration` from latest `origin/main`.
2. Merge the feature/closeout tip(s).
3. Resolve conflicts preserving both intents (e.g. BaseGraphCanvas + Article 16).
4. Run constitution / UI constitution / arch_lint / pytest / Tom.
5. Merge the integration branch to `main`.
6. Re-run Repository Truth Audit; delete superseded branches.
