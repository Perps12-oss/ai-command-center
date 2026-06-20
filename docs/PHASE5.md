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

## Phase 5C — Daily driver stress test (current)

System reality audit — **observe, do not change code** during the test.

| Layer | Focus |
|-------|--------|
| 1 | Core loop (Alt+Space, commands, clipboard, notes, shell) |
| 2 | Context stress (chaos, long sessions, conflicting inputs) |
| 3 | UI ergonomics (does UI disappear while staying usable?) |
| 4 | Failure modes (Ollama down, empty clipboard, spam, reconnect) |

**Preflight:** `python scripts/verify_phase5c_preflight.py`  
**Scorecard:** `python scripts/phase5c_scorecard.py record`  
**Gate:** `python scripts/verify_phase5c.py` (preflight + gold-standard scores)

Full protocol: [PHASE5C_STRESS_TEST.md](PHASE5C_STRESS_TEST.md)

## Phase 5C+ — Telemetry layer (observation only)

Passive EventBus passthrough → `telemetry_events` SQLite. **Dumb at runtime** — all behavioral interpretation offline.

| Piece | Role |
|-------|------|
| `TelemetryService` | Raw bus event → SQLite (no inference) |
| `telemetry_summary.py` | Offline correlation, hesitation, retries, friction score |

**Gate:** `python scripts/verify_phase5c_telemetry.py`

```powershell
& $py scripts/telemetry_summary.py
```

## Still out of scope

Semantic search, multi-chat, agents, autonomous loops.
