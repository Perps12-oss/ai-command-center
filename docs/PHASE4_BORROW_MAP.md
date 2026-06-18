# Phase 4 Borrow Map v2 — Traceable References

Inspect these repos for **patterns only**. Do not add LangChain, AutoGPT, or Neo4j as dependencies.

---

## 4B — Tool Execution Core

| Reference | URL | Steal | Ignore |
|-----------|-----|-------|--------|
| Codex | https://github.com/openai/codex | Single-step tool execution | Agent loops |
| LangChain | https://github.com/langchain-ai/langchain | Tool schema + registry | Chains, memory agents |
| AutoGPT | https://github.com/Significant-Gravitas/AutoGPT | ReAct contrast only | Autonomous loops |

**Project mapping:** `core/tools.py`, `tool_registry_service.py`, `tool_executor_service.py`

---

## 4C — Overlay Engine

| Reference | Steal | Ignore |
|-----------|-------|--------|
| Seeva-style overlays | Always-on-top, hotkey activation | Electron stack |
| AIPointer / Tauri widgets | Cursor-attached popups | Stack migration |

**Project mapping:** `ui/app.py` compact mode, `overlay.*` events

---

## 4D — Context Compression

| Reference | Steal | Ignore |
|-----------|-------|--------|
| OpenYak-style compression | Token budget, sliding window | Embedding retrieval |
| Claude pruning (documented) | Structured section packing | Semantic ranking |

**Project mapping:** `core/context_manager.py` summarization hook

---

## 4E — Memory Graph

| Reference | Steal | Ignore |
|-----------|-------|--------|
| Neo4j model | Entity → relationship | Neo4j server |
| Obsidian graph | Vault-backed structure | Auto-ingestion |
| Row-Bot patterns | Tiered memory | Vector DB primary |

**Project mapping:** `memory_nodes` / `memory_edges`, `MemoryGraphService`

---

## 4F — Ollama Router

| Reference | URL | Steal | Ignore |
|-----------|-----|-------|--------|
| Jan | https://github.com/janhq/jan | Model abstraction | Auto-switching agents |
| Chatbox | https://github.com/Bin-Huang/chatbox | Task → model map | Multi-chat default |

**Project mapping:** `model_router_service.py`, `model_registry.py`

---

## Divergence layer

| Unique to AI Command Center | vs borrowed |
|-----------------------------|-------------|
| UCGS gate-by-gate + violation registry | Feature-first shipping |
| EventBus-only integration | Direct UI ↔ service coupling |
| Explicit context only | Implicit memory expansion |
| CommandRouter classify-only | ReAct execute-and-loop |
| Windows ARM64 local-first | Cross-platform clients |
| Single session daily-driver | Multi-chat by default |

**Highest drift risk:** Tool registry (4B). Mitigation: max one tool per `command.routed`; no planner service.
