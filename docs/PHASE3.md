# Phase 3 — Scope, Gates, and Discipline

Phase 3 goal: **one useful daily-driver loop** — not feature breadth.

```text
Alt+Space → ask question → streamed answer → close → history persists
Target: < 10 seconds for "Summarize this clipboard"
```

---

## Subphases (gate-by-gate)

| Subphase | Scope | Gate |
|----------|--------|------|
| **3A** | ContextBundle, ContextManager, OllamaService **interface**, command routing | `verify_phase3a.py` — no HTTP |
| **3B** | Ollama HTTP, streaming, cancel, error handling | cancel + offline recovery |
| **3C** | ObsidianService, FTS search, note injection | `note:` → context sources |
| **3D** | Single-session SQLite, chat view, UX | daily driver < 10s |

### 3D note-integration audits (from 3C review)

Run before signing off Phase 3D — baseline for Phase 4 indexing work:

```powershell
python scripts/audit_note_integration.py
```

| Test | What it checks |
|------|----------------|
| **First search latency** | Cold `note:` search — records `vault_files`, `vault_bytes`, `index_ms`, `search_ms` |
| **Context pollution** | Select Note A → search Note B (no select) → chat — only A in `ContextBundle` |

**3A status:** OllamaService ABC + `StubOllamaService`, `ChatHandlerService`, `model_registry` stub.

**3B status:** `OllamaHttpService` (aiohttp `/api/chat`), cancel via asyncio, offline errors, minimal `ChatView` streaming UI.

**3C status:** `ObsidianService` (FTS5 keyword search, read/write), `NotesView`, opt-in note injection via `ContextManager`.

**3D status:** `SessionService` + `ConversationRepository`, `chat.history_loaded`, clipboard-on-demand, markdown code fences, thread-safe `UIQueue`.

---

## Build order (mandatory)

| Order | Module | Rule |
|-------|--------|------|
| **1** | `context_manager.py` | **Before any Ollama code.** Every AI request passes through it. |
| 2 | `OllamaService` | Load, stream, cancel, unload only |
| 3 | `ObsidianService` | Search, read, write markdown only |
| 4 | Chat view | Single session UI, streaming markdown |

**No AI call may bypass `ContextManager.build_context()`. Ever.**

---

## Phase 3 allowed (only 4 things)

### 1. OllamaService

- Load model
- Send prompt (from `ContextBundle` only)
- Stream response
- Cancel response
- Unload model

### 2. ObsidianService

- Search markdown (FTS5 keyword — **not** semantic)
- Read note
- Write note

### 3. ContextManager (V1)

```python
build_context(query, clipboard=None, notes=None) → ContextBundle(prompt, sources, token_estimate)
```

- Token budget enforcement (70% fill ratio default)
- Source attribution
- **No** embeddings, vectors, ranking, or scraping

### 4. Chat view

- **Single session** with persistent history (not multi-chat / folders / pins)
- Streaming UI
- Markdown + code blocks (batched 50ms)

---

## Explicitly banned in Phase 3

| Feature | Phase |
|---------|-------|
| Semantic search | 4+ |
| Embeddings | 4+ |
| sqlite-vec | 4+ |
| OCR | 4+ |
| Active window scraping | 4+ |
| Clipboard monitoring (background) | 4+ |
| Auto-memory | 4+ |
| Voice | 6 |
| Agents | 5 |
| Workspace profiles | 5 |
| Multi-chat / folders / pinned chats | 4+ |

---

## CommandRouter — stay dumb

`CommandRouterService` does **intent detection + routing only**.

Forbidden in CommandRouter:

- Planning
- Reasoning
- Orchestration
- Multi-step agent loops

Otherwise Phase 5 accidentally gets a second agent framework.

---

## Anti-pattern (do not build)

```text
User Prompt → Ollama → Display
(then bolt on clipboard, notes, window, memory later → prompt builder mess)
```

Required pattern:

```text
User input → CommandRouter → handler
    → ContextManager.build_context(...)
    → OllamaService.stream(ContextBundle.prompt)
    → EventBus → Chat view
```

---

## Phase 3 review gates

### User experience gate

Can a non-developer understand how to ask a question? (command box + chat view)

### Prompt assembly gate

Does **every** AI request pass through `ContextManager`? (grep / test enforcement)

### Cancellation gate

Can a running Ollama stream be cancelled without freezing UI?

### Failure recovery gate

If Ollama is offline: UI responsive + clear user feedback (no hang, no silent fail)

### Daily driver test

1. Alt+Space
2. Ask: "Summarize this clipboard"
3. Get answer
4. Close palette

All in **< 10 seconds**, without UI freeze, memory spike, or manual refresh.

If this passes → **Project status: Useful**

---

## Chat scope (product discipline)

**First implementation:**

- Single session
- Persistent history in SQLite (`conversations` / `messages` — one active row)

**Not in v1:**

- Chat 1 / Chat 2 / Chat 3
- Folders, projects, pinned chats

Verify after Phase 3:

- Can I ask a question?
- Can I get an answer?
- Can I close and reopen?
- Does history persist?

---

## Health snapshot (pre-Phase 3)

| Area | Status |
|------|--------|
| Architecture | Excellent |
| State management | Excellent |
| UI isolation | Excellent |
| Service lifecycle | Excellent |
| Scope discipline | Excellent |
| Context management | **Next major risk — mitigated by ContextManager first** |
| Prompt assembly | Must stay centralized |
| Product complexity | Watch multi-chat temptation |
| Ollama integration | Ready to implement |
| Obsidian integration | Ready to implement |
