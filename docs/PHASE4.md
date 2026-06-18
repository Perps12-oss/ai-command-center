# Phase 4 — Evolution Under Load

Phase 4 shifts from “architecture works” to “architecture stays stable as features grow.”

Gate-by-gate. Each subphase has a verify script and ledger update.

**Borrow map:** see [PHASE4_BORROW_MAP.md](PHASE4_BORROW_MAP.md) for traceable reference repos.

---

## Global invariants

```text
NO AGENTS · NO CHAINS · NO AUTONOMOUS LOOPS
ONLY: intent → tool → result
```

Phase 3 bans remain: no embeddings, sqlite-vec, semantic search, multi-chat, auto-memory, background clipboard.

---

## Phase 4A — Async Obsidian indexing (DONE — V-001)

**Gate:** `python scripts/verify_phase4a.py`

- Background `obsidian-index` worker thread
- Events: `note.index_progress`, `note.index_complete`
- EventBus handler: FTS SQLite only + enqueue index job

---

## Phase 4B — Tool Execution Core

**Borrow:** LangChain tool schema pattern, Codex single-step execution (no LangChain dependency).

**Deliverables:**

- `core/tools.py` — `ToolSpec`, `ToolResult`
- `services/tool_registry_service.py` — register tools by name
- `services/tool_executor_service.py` — `tool.invoke` → one tool → `tool.result` / `tool.error`
- `services/shell_tool_service.py` — bridges `INTENT_SHELL` (`>` prefix) to `tool.invoke`
- Contract: `tool.invoke` / `tool.result` v1.0

**Gate:** `python scripts/verify_phase4b.py`

---

## Phase 4C — Overlay Engine

**Borrow:** Seeva/AIPointer overlay *behavior* (stack stays Tk/Python).

**Deliverables:**

- `overlay.show` / `overlay.hide` / `overlay.anchor` events
- Compact always-on-top overlay mode in `ui/app.py`
- Settings UI panel via `settings.set_request`

**Gate:** `python scripts/verify_phase4c.py`

---

## Phase 4D — Context Compression Engine

**Borrow:** OpenYak-style thread compression (no vector retrieval).

**Deliverables:**

- `ContextManager` compresses oldest history into `conversation_summary` when over budget
- `CONTEXT_BUNDLE_VERSION` → `1.1`

**Gate:** `python scripts/verify_phase4d_compression.py`

---

## Phase 4E — Memory Graph System

**Borrow:** Neo4j entity-relationship *model*, Obsidian graph structure (SQLite storage).

**Deliverables:**

- `memory_nodes` / `memory_edges` tables
- `MemoryGraphService` — opt-in `memory.remember` only
- `ContextManager.build_context(graph_snippets=...)`

**Gate:** `python scripts/verify_phase4e.py`

---

## Phase 4F — Ollama Router + Model Classifier

**Borrow:** Jan AI / Chatbox task → model mapping patterns.

**Deliverables:**

- `services/model_router_service.py` — static intent → model map
- `ChatHandler` queries router before `stream_chat()`
- `model.selected` event

**Gate:** `python scripts/verify_phase4f.py`

---

## Regression suite

```powershell
$py = "C:\Users\S8633\AppData\Local\Python\bin\python.exe"
& $py scripts/verify_contracts.py
& $py scripts/verify_phase3d.py
& $py scripts/verify_phase4a.py
& $py scripts/verify_phase4b.py
& $py scripts/verify_phase4c.py
& $py scripts/verify_phase4d_compression.py
& $py scripts/verify_phase4e.py
& $py scripts/verify_phase4f.py
& $py scripts/audit_note_integration.py
& $py scripts/run_daily_driver.py
```
