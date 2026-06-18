# Violation Registry (UCGS v3)

Formal classification of open architectural debt. Update when status changes.

---

## V-001 — Sync I/O on EventBus thread (Obsidian)

| Field | Value |
|-------|--------|
| **Severity** | S2 |
| **Status** | **ACCEPTED DEBT** (defer fix to Phase 4A) |
| **Location** | `ObsidianService._index_vault_incremental()` — synchronous `rglob` + file read on `command.routed` handler thread |
| **Impact** | Large vaults can stall EventBus briefly; UI remains responsive via `UIQueue` for display |
| **Mitigation (now)** | On-demand indexing only; mtime skip on re-index; `audit_note_integration` baseline (~43 ms / 40 files) |
| **Resolution target** | Phase 4A — background index worker thread + `note.index_progress` events |
| **Escalation** | If user-visible freeze on real vault → bump to S3, prioritize 4A |

**Classification rationale:** Architectural boundary is correct (Obsidian owns vault I/O). Failure mode is performance, not pipeline bypass. Accept until Phase 4.

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
| **Status** | **PROCESS DEBT** (open) |
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
