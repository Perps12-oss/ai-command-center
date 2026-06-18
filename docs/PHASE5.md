# Phase 5 — Daily-Driver Integration

Phase 5 wires Phase 4 backend capabilities into the command palette UX.

## Phase 5A — UI integration (current)

| Feature | Command / event | UI behavior |
|---------|-----------------|-------------|
| Shell tools | `> echo hello` | `tool.result` → Chat view |
| Memory store | `remember: label \| content` | `memory.stored` → system message |
| Memory select | `memory: keyword` | injects into next chat via ContextManager |
| Model router | summarize queries | `model.selected` → top bar model label |

**Gate:** `python scripts/verify_phase5a.py`

## Phase 5B — Plugin registry skeleton

| Piece | Role |
|-------|------|
| `plugins/manifests/*.yaml` | Declarative plugin definitions (no dynamic imports) |
| `PluginRegistryService` | Loads manifests, publishes `plugin.catalog` |
| `PluginsView` | Sidebar panel — catalog from EventBus |

**Gate:** `python scripts/verify_phase5b.py`

## Still out of scope

Semantic search, multi-chat, agents, autonomous loops.
