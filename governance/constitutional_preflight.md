# Constitutional Pre-Flight — Performance Architecture

**Branch:** `cursor/perf-architecture-freeze-f2e9`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

Eliminate UI freezes and sync bottlenecks without changing user-visible behaviour or APIs.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation (no direct storage/Ollama/tools) | Preserved; Performance Inspector reads AppState/EventBus metrics only |
| No service-to-service calls | Preserved |
| Host supremacy | N/A |
| Contracts / topics | No topic removals; behaviour-preserving handlers |

## Behaviour preservation

- Same EventBus topics and payloads
- Same navigation outcomes (one click → one navigate → one render)
- Same settings semantics (one logical change → one snapshot)
- Telemetry still persisted (async batch)
- Inspectors show the same data (dirty update, not full wipe when unchanged)

## Risk

Medium — AppState reducer indexing and identity-based dirty detection must not drop updates. Covered by existing AppState projection tests + new perf benchmarks.
