# Violation Registry (UCGS v3)

Formal classification of open architectural debt. Update when status changes.

---

## V-001 — Sync I/O on EventBus thread (Obsidian)

| Field | Value |
|-------|--------|
| **Severity** | S2 |
| **Status** | **CLOSED** (Phase 4A async indexer) |
| **Location** | Was: `ObsidianService._index_vault_incremental()` on EventBus thread |
| **Resolution** | Background `obsidian-index` worker; `note.index_progress` / `note.index_complete` events |
| **Gate** | `scripts/verify_phase4a.py` |

---

## V-002 — Contract schemas without version field

| Field | Value |
|-------|--------|
| **Severity** | S2 → **S1 (mitigated)** |
| **Status** | **CLOSED** (contract lock 3D→4) |
| **Resolution** | `ContextBundle.version`, `command.routed.contract_version`, `OllamaServiceBase.api_version` + aliases `chat`/`stream` |
| **Gate** | `scripts/verify_contracts.py` |
| **Docs** | `docs/CONTRACTS.md` |

---

## V-006 — Large uncommitted diff (Phases 1–3D)

| Field | Value |
|-------|--------|
| **Severity** | S3 (governance / reproducibility) |
| **Status** | **CLOSED** (commit `592c0e9`) |
| **Impact** | No versioned artifact for Phases 1–3D; regression baseline tied to working tree only |
| **Resolution** | Git commit (single or split PRs) before Phase 4 feature work |
| **Owner** | Maintainer — explicit `git commit` when ready |
| **Not a runtime defect** | Architecture verified by gate scripts on current tree |

**Classification rationale:** Process risk, not architecture-breaking. Does not block Phase 4 design work; blocks production release narrative.

---

## Closed violations (reference)

| ID | Summary | Closed |
|----|---------|--------|
| V-003 | NoteRepository mtime/body swap | 3C |
| V-004 | ChatHandler infinite `command.routed` loop | 3A |
| V-005 | Tk `after()` from Ollama worker thread | 3D UIQueue |
