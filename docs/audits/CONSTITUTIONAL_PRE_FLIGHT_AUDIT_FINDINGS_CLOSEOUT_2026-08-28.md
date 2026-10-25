# Constitutional Pre-Flight — Architecture Audit Findings Closeout

| Field | Value |
|-------|-------|
| **Date** | 2026-08-28 |
| **Task** | Close out verified findings from `ARCHITECTURE_FIRST_REPO_AUDIT_2026-08-28.md` on `origin/main` @ `66be7de` |
| **Branch** | `cursor/audit-findings-closeout-dfc2` |

## Authorities Reviewed

- `PROJECT_CONSTITUTION_V4.md` (Inv 1–2, 11–12, Art XVII)
- `PERFORMANCE_CONSTITUTION.md` (Art III/IV/X — sync ≤5 ms; no long block on dispatch)
- `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md` (UI isolation, no service→service)
- `docs/ARCHITECTURE.md`, ADR-006, ADR-018
- Audit: `docs/audits/ARCHITECTURE_FIRST_REPO_AUDIT_2026-08-28.md`

## Task Description

Repair verified defects without redesigning architecture:

1. P0 — Offload shell `communicate` from EventBus async dispatch thread  
2. P0 — Keep `UI_COMMAND` SYNC_CRITICAL; defer post-admit dispatch to ASYNC_ELIGIBLE  
3. P1 — Secret fail-closed / qwenpaw keyring / redact bus payloads  
4. P1 — UI Rule 1: workflow I/O, startfile, webbrowser, SystemView via bus/services  
5. P2 — Shared shell runner; gate `ActionRegistry.invoke`; fix stale docs  
6. P3 — Tighten headless CI perf floors toward Art IV (no Win soak claim)

## Protected Assets Impacted

- EventBus topics / dispatch policy (new ASYNC topic(s); shutdown policy unchanged in spirit)
- Tool Runtime / Capability execution (worker handoff, same TOOL_INVOKE publisher)
- Settings / secret handling
- AppState projection of settings (redacted)

## Sources of Truth Impacted

- Settings secret storage (keyring-first, fail-closed)
- System metrics SoT remains SystemMonitorService (UI stops parallel psutil)

## Architectural Invariants Impacted

- Inv 2 UI isolation — restore compliance for soft breaches  
- Inv 12 — close latent ActionRegistry.invoke outside tests  
- Perf Art X — remove long communicate on dispatch thread  
- ADR-006 — EA remains sole intake; UI_COMMAND stays SYNC_CRITICAL  

## Contracts Impacted

- `topics.py` — add dispatch/export/launch topics as needed  
- SettingsSnapshot bus payload redaction  

## Gate Impact Assessment

- Existing receipt / sandbox / authority tests must remain green  
- Perf CI floors tightened after P0  

## Historical Gate Impact

- None weakened  

## Regression Risk

- Shell cancel/shutdown races; settings migration for existing plaintext keys; UI export UX  

## Constitutional Status

**APPROVED** — implementation may begin.
