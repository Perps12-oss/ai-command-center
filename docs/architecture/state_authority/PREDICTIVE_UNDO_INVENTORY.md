# PredictiveEngine & UndoReplay Inventory (State Authority / R1 P5)

**STATUS:** RETIRED FROM LIVE (ADR-014) — inventory only, **not Queue 1**

**HISTORICAL / NON-AUTHORITATIVE as implementation work**

PredictiveEngine and UndoReplay are **RETIRED / NON-CANONICAL**. Do not restore or wire them without a superseding ADR.

**Authority:** `STATE_AUTHORITY_CONTRACT.md`, ADR-006, ADR-014 (ADR-005 original wording is SUPERSEDED)  
**Date:** 2026-08-04  
**Baseline:** `origin/main` @ `7d1065b`

## Verdict

**PredictiveEngine** and **UndoReplay** are Phase-10 research packages with unit
tests only. They are **not** on the live composition root. Live timeline undo /
snapshots / WM recovery already own adjacent concerns. **RETIRED from live
(ADR-014).** No silent-merge into SA mutate. No factory wire in this slice.

| Path | Stack | On SA path? | Disposition |
|------|-------|:-----------:|-------------|
| **A — Live substitutes** | `TimelineService`, `SnapshotService`, WM `recover`, BrainSituationPanel heuristics | ⚠️ adjacent | **keep** — product SoT for undo/snapshot/heuristic blockers |
| **B — Research dual** | `PredictiveEngine`, `undo_replay.Timeline` | ❌ | **RETIRED from live (ADR-014)** |

---

## Path A — Live adjacent (do not displace)

| Surface | Role |
|---------|------|
| `TimelineService` + `TIMELINE_UNDO_*` | Live timeline undo intents |
| `SnapshotService` | Durable checkpoints |
| `WorldModel.recover` / mutation journal | SA-backed reconstruction |
| BrainSituationPanel “Prediction / Blockers” | UI heuristics from AppState — **not** PredictiveEngine |

---

## Path B — Research packages

```text
core/world_model/predictive_engine/engine.py  → in-memory predictions; no EventBus
core/world_model/undo_replay/timeline.py      → in-memory Timeline + Snapshot; no repo
```

Evidence:

| Probe | Finding |
|-------|---------|
| Factory | No construct / register |
| Persistence | In-memory only |
| EventBus | None |
| Tests | `tests/core/world_model/predictive_engine/`, `…/undo_replay/` |

---

## Migration plan

| Step | Action | Gate |
|------|--------|------|
| **P5a ✅** | Inventory + ADR-014 + pins | This PR |
| P5b | Optional later: prediction projection ADR (read-only, SA-aligned) | New ADR |
| P5c | Optional later: unify undo under TimelineService only — never dual UndoReplay | New ADR |
| ❌ | Factory-wire either package without ADR | Forbidden |
| ❌ | UndoReplay `StateProvider.restore_*` bypassing SA.mutate | Forbidden |

---

## References

- `docs/architecture/adr/ADR-014_PREDICTIVE_UNDO_DISPOSITION.md`  
- `docs/architecture/SHADOW_SOT_INVENTORY.md`  
- `ai_command_center/core/world_model/predictive_engine/`  
- `ai_command_center/core/world_model/undo_replay/`  
- `ai_command_center/core/service_factory.py`  
