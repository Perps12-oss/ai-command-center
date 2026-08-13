# Constitutional Pre-Flight — Vendor Cursor skills (project-scoped)

**Date:** 2026-08-13  
**Branch:** `cursor/vendor-cursor-skills-d598`  
**Baseline:** `origin/main` @ `7406323`  
**Change class:** Agent tooling only (`.cursor/skills/` + gitignore exception + this audit). No product runtime, contracts, or Queue 1 work.

---

## Authority read

| Layer | Document | Status |
|-------|----------|--------|
| L1 | `PROJECT_CONSTITUTION_V4.md` | Read — Art. 0 (tooling ≠ architecture), Art. X pre-flight |
| L2 | `AGENTS.md`, `docs/ARCHITECTURE_ENFORCEMENT.md` | Read — UI isolation, EventBus ownership, Cloud skill discovery |
| Guide | `docs/governance/IMPLEMENTATION_GUIDE.md` | Read — Queue 1 EMPTY; this is owner-requested tooling, not invented backlog |
| L3 | `docs/ARCHITECTURE.md`, `ai_command_center/core/events/topics.py` | Confirmed; not amended |
| ADRs | Index consulted; next free = ADR-024 | No ADR required |
| Stop line | `docs/audits/R1_UNGATED_STOP_LINE.md` | Unchanged |

---

## Intent

1. Skip `claude-token-monitor-setup` (not a Cursor product; use Spending dashboard).  
2. Vendor five project-scoped skills under `.cursor/skills/` so Cloud Agents and Desktop `/` discovery can load them from the clone: `pytest`, `http-api-testing-httpx`, `hallmark`, `theme-factory`, `ui-ux-pro-max`.  
3. Local `~/.claude/skills/` copies are absent on this Cloud VM; source from public GitHub skill trees (or ACC wrappers occupying the requested names, matching existing `.claude/skills/*` pattern).  
4. Un-ignore skill `data/` so ui-ux-pro-max catalogs are not dropped by the root `data/` gitignore rule.

---

## Invariants touched

| Invariant / rule | Impact |
|------------------|--------|
| Skills are not Level-1/2 authority | Vendored skills must defer to Constitution / ADRs; ACC wrappers state this |
| UI isolation / no HTTP product API | `http-api-testing-httpx` must not authorize adding FastAPI/HTTP servers |
| Inv 13 host supremacy | Skills do not introduce third-party consoles or shadow persistence |
| Queue 1 EMPTY | No product features; no phase-complete claim |
| `.cursor/skills/` tracked | `.gitignore` already allows `.cursor/skills/**`; add `data/` exception |

---

## Out of scope

- Marketplace `/plugin` install (Desktop-only; Cloud vendors the generated skill tree instead)  
- `claude-token-monitor-setup`  
- Product UI redesign, CustomTkinter restyle, or runtime architecture changes  
- Duplicating skills into `.claude/skills/` (user asked `.cursor/skills/` only)  
- Amending Constitution, ADRs, or IMPLEMENTATION_GUIDE Queue 1  

---

## Verification planned

- Confirm each `SKILL.md` exists, is readable, and YAML `name:` matches folder.  
- Confirm `ui-ux-pro-max/data/` is tracked (not gitignored).  
- `python3 scripts/verify_constitution.py`  
- Cheap gates as applicable; no pytest delta expected (no product code).  

---

## Verdict

**Pre-flight COMPLETE.** Tooling vendoring may proceed.
