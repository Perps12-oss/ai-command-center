# Next Session TODO
> Delete this file when all items are complete.

---

## ✅ Completed (audit refactor — 2026-06-29)

| # | Item |
|---|------|
| 1 | Remove `ConversationRepository` shim from `db/repository.py` |
| 2 | Replace UIQueue 50ms polling with event-driven `<<UIQueueItem>>` wake-up |
| 3 | Fix `OllamaHttpService._on_unload` asyncio zombie-thread risk |
| 4 | Extract all service wiring from `application.py` into `core/service_factory.py` |
| 5 | Replace `_ensure_view` if/elif chain in `ui/app.py` with `_view_registry` dict |
| 6 | Doc cleanup — consolidated 25+ files into `docs/ARCHITECTURE.md` |
| 7 | SQLite migration runner — versioned chain replacing ad-hoc `IF NOT EXISTS` guards |

---

## ⏳ Pending

### Track 6.4 — Vector search / memory graph enhancements
**Priority:** High | **Status:** Unblocked — start here

Add embeddings-based memory retrieval:
- Add vector storage to `MemoryGraphService` / `MemoryRepository`
- Wire similarity search through EventBus: `memory.search_request` → `memory.search_result`
- Surface ranked results in `ContextManager` as an opt-in injection source
- No direct repository access from UI — all reads via AppState projection

---

### Track 6.5 — Multi-agent runtime
**Priority:** High | **Status:** GATED — design work required first

**Do not write any code until the gate is cleared.**

Gate doc: `docs/ARCHITECTURE_REVIEW_MULTI_AGENT.md`

Required before implementation:
1. Answer constitutional questions A1 (context assembly), A2 (execution-before-explanation), A5 (determinism-before-AI), and the system-level agent spawning question
2. Produce the 6 required deliverables: data-flow diagram, new EventBus topic list, service decomposition diagram, constitutional question mapping, forbidden execution paths list, verification plan
3. Complete the sign-off checklist in the gate doc
4. Absorb the signed decisions into `docs/ARCHITECTURE.md`
5. Delete `docs/ARCHITECTURE_REVIEW_MULTI_AGENT.md`
6. Only then implement

---

### SQLite migration runner — ongoing housekeeping
**Priority:** Low | **Status:** No action needed until a new table is required

Runner is live at **v2** in `repositories/database_bootstrap_repository.py`.

To add a future migration:
1. Define `_migrate_vN(conn: sqlite3.Connection) -> None` in that file
2. Append `(N, _migrate_vN)` to `_MIGRATIONS`
3. N must be `max(existing) + 1`
4. No edits to `schema.sql` required
