# Constitutional Pre-Flight — PR-UI-E05 Memory Workspace

**Slice:** PR-UI-E05 — Memory Workspace  
**Roadmap:** `docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md`  
**Baseline:** `origin/main` @ `a375553` (post-E04 Tom audit)  
**Builder:** Cursor (sole coder + Tom auditor)

---

## Authority checks

- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/UI_CONSTITUTION.md` — Article 21 (UI reads AppState / publishes events)
- [x] `docs/agents/CURSOR_AUDIT_GATE.md`
- [x] `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`
- [x] Roadmap E05 section

---

## Scope

Evolve existing `MemoryView` into a workspace with:

1. Catalog list via `MemoryCard`
2. Detail pane via `MemoryDetail`
3. Search (local filter)
4. Injection indicator aligned with `memory_selected` / global context sources
5. Inspector select hooks (`kind=memory`)
6. `UI_MEMORY_*` intents on EventBus

No E06–E13. No new memory authority path — reuse `MEMORY_REMEMBER` / `MEMORY_DELETE_REQUEST` / `MEMORY_SELECTED`.

---

## AppState

- New fields: **none** (optional presentation helpers only)
- Continue projecting `memory_catalog` / `memory_selected` / `notes_memory`

---

## Risks / deferrals

- Catalog projection today carries `label` / ids, not full content body — detail shows available fields; content body remains service-backed via remember payload when present in UI-local items.
- Multi-view inspector dock sync remains E01 deferral (chat-primary).

---

## Pre-flight verdict

**GO** — implement on `origin/main` @ `a375553`.
