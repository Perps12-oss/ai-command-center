# Phase Ledger

Update the **Current** block at every phase boundary (before starting the next phase and after gate PASS).

---

## Current

```
Current Phase: Phase 4A — COMPLETE (4B+ not started)
Mode: Gate-by-gate
Previous Phase Snapshot: Phase 3D PASS + contracts v1.0 locked; commit 592c0e9 (V-006 closed)
Pre-Commit Diff: Phase 4A async Obsidian indexer — uncommitted
Historical Ledger: See table below
```

### Gate status (latest run)

| Gate | Script | Result |
|------|--------|--------|
| Phase 1 | `verify_phase1.py` | PASS |
| Phase 2 | `verify_phase2.py` | PASS |
| ContextManager | `verify_context_manager.py` | PASS |
| Phase 3A | `verify_phase3a.py` | PASS |
| Phase 3B | `verify_phase3b.py` | PASS |
| Phase 3C | `verify_phase3c.py` | PASS |
| Note audits | `audit_note_integration.py` | PASS |
| Phase 3D | `verify_phase3d.py` | PASS |
| Contracts v1.0 | `verify_contracts.py` | PASS |
| Phase 4A | `verify_phase4a.py` | PASS |

### Phase 3D deliverables (this phase)

- `ConversationRepository` + `SessionService` — single session `default`, SQLite persistence
- `chat.history_loaded` → ChatView restore on startup
- `ChatHandler` — `conversation_history` from DB; user/assistant append
- Clipboard on-demand when query mentions "clipboard" (no background monitor)
- `ChatView` — history load, code-fence markdown display
- `UIQueue` — thread-safe `SimpleQueue` main-thread poll

### Phase 4A deliverables

- Background `obsidian-index` worker — vault `rglob` off EventBus thread (V-001 closed)
- Events: `note.index_progress`, `note.index_complete`
- `note.search_results.indexing` + auto-refresh after index

### Next

- **Manual daily-driver** — `docs/DAILY_DRIVER.md` (still pending sign-off)
- Phase 4B: plugin registry skeleton (see `docs/PHASE4.md`)
- Phase 4C+: settings UI, shell handler

---

## Historical Ledger

| Phase | Tag | Mode | Gate | Snapshot (one line) |
|-------|-----|------|------|---------------------|
| 0 | `Phase 0` | Preflight | `preflight_arm64.py` PASS | ARM64 scaffold, Ollama PE check, baseline.json, compatibility_matrix |
| 1 | `Phase 1` | Infrastructure | `verify_phase1.py` PASS | EventBus, AppState, ServiceManager, SQLite settings, application.py |
| 2 | `Phase 2` | UI shell | `verify_phase2.py` PASS | 1100×700 palette, Alt+Space, tray, UIController bus-only |
| 2 fix | `Phase 2 review` | Hardening | — | Removed ApplicationCore from UI; CommandRouter; lazy views |
| 3 prep | `ContextManager` | Gate | `verify_context_manager.py` PASS | ContextBundle, build_context(), token budget |
| 3A | `Phase 3A` | Gate-by-gate | `verify_phase3a.py` PASS | OllamaService ABC + stub, ChatHandler skeleton, model_registry |
| 3B | `Phase 3B` | Gate-by-gate | `verify_phase3b.py` PASS | OllamaHttpService streaming, cancel, offline errors, ChatView |
| 3C | `Phase 3C` | Gate-by-gate | `verify_phase3c.py` PASS | ObsidianService FTS5, NotesView, note injection via ContextManager |
| 3D | `Phase 3D` | Gate-by-gate | `verify_phase3d.py` PASS | Session persistence, history in context, clipboard path, UIQueue fix |
| 4A | `Phase 4A` | Gate-by-gate | `verify_phase4a.py` PASS | Async Obsidian vault indexer, index progress events, V-001 closed |

---

## Template (copy for next phase)

```
Current Phase: {PHASE_TAG}
Mode: {MODE}
Previous Phase Snapshot: {PREV_STATE}
Pre-Commit Diff: {DIFF}
Historical Ledger: docs/PHASE_LEDGER.md § Historical Ledger
```

### Example after starting Phase 4A

```
Current Phase: Phase 4A — IN PROGRESS
Mode: Gate-by-gate
Previous Phase Snapshot: Phase 3D PASS — SessionService, chat.history_loaded, clipboard on-demand, verify_phase3d PASS; manual daily-driver: {PASS|FAIL|pending}
Pre-Commit Diff: {git status --short summary or commit SHA range}
Historical Ledger: docs/PHASE_LEDGER.md § Historical Ledger
```

---

## Pre-commit diff log (manual)

Record a short diff summary when closing each phase (before git commit).

| Closed | Branch / state | Diff summary |
|--------|----------------|--------------|
| Phase 0 | `c7642e9` on master | Phase 0 ARM64 preflight scaffold committed |
| Phases 1–3D | `592c0e9` on master | Full app + contracts v1.0 |
| Phase 4A | uncommitted | Async Obsidian indexer |

---

## UCGS v3 Governance Snapshot

Update this section after each phase gate and before Phase 4+ work.

**Audit:** STRICT | **Phase:** 4A | **Verdict:** `CONDITIONAL_APPROVE`

V-001 and V-006 closed. Remaining: manual daily-driver sign-off.

### Input context (frozen at audit)

```
Current Phase: Phase 3D — COMPLETE (manual daily-driver sign-off pending)
Mode: Gate-by-gate (STRICT)
Previous Phase Snapshot: Phase 3C PASS — Obsidian FTS, opt-in injection, audit_note_integration PASS
Pre-Commit Diff: Phases 1–3D uncommitted; HEAD c7642e9 = Phase 0 only
Historical Ledger: § Historical Ledger above
```

### Architecture compliance

| Rule | Status |
|------|--------|
| UI → no Ollama/Obsidian/DB direct access | PASS |
| CommandRouter → classify only | PASS |
| ContextManager → assembly only | PASS |
| EventBus pipeline | PASS |
| Scope creep (embeddings/agents/multi-chat/auto-context) | PASS |

**S3+ hard violations:** none

### Contract version audit

| Contract | Required v1.0 | Status |
|----------|----------------|--------|
| ContextBundle | `version` + fields | **LOCKED** — `version: "1.0"` |
| command.routed | `contract_version` + metadata | **LOCKED** — `contract_version: "1.0"` |
| OllamaService | `chat` / `stream` / `cancel` | **LOCKED** — aliases + `api_version` |

Gate: `scripts/verify_contracts.py` PASS | Docs: `docs/CONTRACTS.md`

### Violation ledger

| ID | Category | Severity | Status |
|----|----------|----------|--------|
| V-001 | Sync I/O on EventBus (Obsidian vault `rglob`) | S2 | **Closed** (4A async indexer) |
| V-002 | Contract schemas without version field | S2 | **Closed** (contract lock) |
| V-003 | NoteRepository mtime/body swap | S3 | **Closed** (3C fix) |
| V-004 | ChatHandler `command.routed` loop | S3 | **Closed** (3A fix) |
| V-005 | Tk `after()` from worker thread | S2 | **Closed** (3D UIQueue) |
| V-006 | Large uncommitted diff | S3 | **Closed** (`592c0e9`) |

Detail: `docs/VIOLATIONS.md`

### Architecture heatmap

| Zone | Temp | Trend |
|------|------|-------|
| ObsidianService vault scan | **Hot** | Warming |
| ChatHandler (multi-deps) | Warm | Stable |
| EventBus sync dispatch | Warm | Stable |
| OllamaHttpService async thread | Cold | Cooling |
| ContextManager | Cold | Stable |
| UI ↔ bus boundary | Cold | Cooling |

**Trend:** improving | **Debt growth:** stable → slight increase

### Performance baselines (recorded)

| Metric | Value | Source |
|--------|-------|--------|
| Ollama submit latency | ~0.31 ms | `audit_phase3b` |
| Cancel → event | ~11 ms | `audit_phase3b` |
| Cold note index (40 files) | ~43 ms index, ~1 ms FTS | `audit_note_integration` |
| Live daily-driver / startup | pending | manual |

### Plugin readiness (Phase 4)

- EventBus integration pattern: **ready**
- Versioned contracts: **ready** (v1.0 locked)
- Plugin registry / API surface: **not implemented**

### Conditions for full APPROVE

1. Record manual daily-driver in § Current (`docs/DAILY_DRIVER.md`)
2. ~~Commit Phases 1–3D~~ **done** (`592c0e9`)
3. ~~Contract version fields~~ **done**
4. ~~Async Obsidian indexing~~ **done** (4A)

### Machine-readable

```yaml
ucgs_v3:
  phase: "4A"
  verdict: CONDITIONAL_APPROVE
  architecture_trend: improving
  debt_growth_rate: stable
  s3_violations: 0
  open_violations: []
  plugin_ready: partial
  contracts_version: "1.0"
  next_gates: [manual_daily_driver]
```

---

### Manual daily-driver sign-off

```
Status: pending
Date:
Latency (Test A): ___ s
Scores (latency / friction / usability / predictability): /5 each
Blockers:
```

---

*Last updated: Phase 4A gate PASS; V-001/V-006 closed; manual daily-driver pending.*
