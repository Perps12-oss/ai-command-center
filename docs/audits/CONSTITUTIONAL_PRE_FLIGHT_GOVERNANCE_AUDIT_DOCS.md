# Constitutional Pre-Flight — Governance Audit Documentation

**Date:** 2026-08-11  
**Branch:** `cursor/governance-audit-docs-323d`  
**Baseline:** `origin/main` @ `417b8e9`  
**Change class:** Documentation only (audit record + Claude Code operational guide)

---

## Authority read

| Layer | Document | Status |
|-------|----------|--------|
| L1 | `PROJECT_CONSTITUTION_V4.md` | Read — Article 0 (verification ≠ requirements), Article II hierarchy |
| Peer | `PERFORMANCE_CONSTITUTION.md`, `docs/UI_CONSTITUTION.md` | Noted; not amended |
| L2 | `AGENTS.md`, `ARCHITECTURE_ENFORCEMENT.md` | Read — babysit-PR, phase-complete, Cloud caveats |
| Guide | `docs/governance/IMPLEMENTATION_GUIDE.md` | Read — tool-neutral implementation role; precedence restatement |
| L3 | `docs/ARCHITECTURE.md`, contracts, topics | Existence confirmed; not amended |
| ADRs | `docs/architecture/adr/README.md` | Index consulted; next free = ADR-024 |
| Stop line | `docs/audits/R1_UNGATED_STOP_LINE.md` | Hard stops unchanged |

---

## Intent

1. Persist the ACC Governance Audit (sections A–F) under `docs/audits/` as repository truth about governance/tool-parity gaps.  
2. Add root `CLAUDE.md` as a **subordinate** operational guide for Claude Code (and any non-Cursor implementation agent) — extension of IMPLEMENTATION_GUIDE tool-neutrality; **introduces no new governing rules**.

---

## Invariants touched

| Invariant / rule | Impact |
|------------------|--------|
| Art. 0 / Inv 11 SoT | Audit documents gaps (e.g. `.windsurf` UI constitution duplicate); does not create a second architecture.md |
| Tool-neutrality (IMPLEMENTATION_GUIDE) | CLAUDE.md operationalizes parity; does not privilege Claude Code as an authority |
| Phase complete on main | Docs-only; no phase claim |
| Host platform supremacy (Inv 13) | Not changed |

---

## Out of scope (this PR)

- Amending `PROJECT_CONSTITUTION_V4.md` Article II (peer constitutions / ADR level gaps)  
- Deleting `.windsurf/plans/UI_CONSTITUTION-ff006d.md`  
- Wiring `.pre-commit-config.yaml` hooks into the installed UCGS hook  
- Refreshing `TOM_APPROVAL.lock`  
- Any product code, CI workflow, or verifier script changes  

---

## Verification planned

- `python3 scripts/verify_constitution.py`  
- Docs-only: no pytest / arch_lint delta required for merge confidence; run cheap gates before push  

---

## Verdict

**Pre-flight COMPLETE.** Documentation may proceed.
