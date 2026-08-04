# Constitutional Pre-Flight — runtime identity (stale-launch detection)

**Branch:** `cursor/runtime-identity-loud-30d3`  
**Authority:** PROJECT_CONSTITUTION_V4.md

## Intent

Make launch identity impossible to miss so freeze reports from the legacy
OneDrive tree (or any pre-#106/#110 binary) are rejected before further
perf investigation. Print `main` path, cwd, package root, git HEAD, and
`freeze_fix=v6`; add `scripts/verify_runtime_identity.py`.

## Invariants checked

| Invariant | Status |
|---|---|
| UI → AppState → EventBus → Services → Repositories → Storage | Preserved |
| UI isolation | Preserved — identity is launch diagnostics only |
| No new EventBus topics | N/A |
| Host platform supremacy (Inv 13) | N/A |

## Protected assets / sources of truth

- None modified.

## Behaviour preservation

- App still starts; identity lines are additive stdout/stderr.
- No change to Ollama, EventBus dispatch, or UI apply paths.

## Out of scope

- Fixing freezes on stale binaries (impossible until the correct tree is launched)
- Deleting the OneDrive legacy copy (operator action)
