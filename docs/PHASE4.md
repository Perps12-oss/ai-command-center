# Phase 4 — Evolution Under Load

Phase 4 shifts from “architecture works” to “architecture stays stable as features grow.”

Gate-by-gate. Each subphase has a verify script and ledger update.

---

## Phase 4A — Async Obsidian indexing (V-001)

**Problem:** `_index_vault_incremental` ran synchronous `rglob` on the EventBus thread during `note:` search.

**Deliverables:**

- Background `obsidian-index` worker thread
- Events: `note.index_progress`, `note.index_complete`
- `note.search_results.indexing` flag; auto-refresh when index completes
- EventBus handler: FTS SQLite only + enqueue index job

**Gate:** `python scripts/verify_phase4a.py`

**Still banned:** semantic search, embeddings, sqlite-vec, agents, multi-chat

---

## Phase 4B+ (planned — not started)

| ID | Scope | Notes |
|----|--------|-------|
| 4B | Plugin registry skeleton | EventBus-only plugin load |
| 4C | Settings UI panel | bus `settings.set_request` |
| 4D | Shell intent handler | `>` commands |

---

## Regression suite (run after each 4x gate)

```powershell
$py = "C:\Users\S8633\AppData\Local\Python\bin\python.exe"
& $py scripts/verify_contracts.py
& $py scripts/verify_phase3c.py
& $py scripts/verify_phase3d.py
& $py scripts/verify_phase4a.py
& $py scripts/audit_note_integration.py
```
