# Phase 6 - Release Hardening and Operational Readiness

Phase 6 starts after Phase 5 completion and focuses on making the system release-ready.

## Entry criteria

| Criterion | Requirement |
|-----------|-------------|
| Phase 5 complete | `phase-5-complete-20260620` tag exists |
| Core gates | Phase 5A, 5B, 5C, and 5C+ telemetry gates PASS |
| Architecture baseline | No Severity A violations in latest enforcement report |

## Scope

| Area | Goal |
|------|------|
| Packaging | Define reproducible release build flow for Windows daily-driver deployment |
| CI hardening | Run full gate bundle in CI with clear pass/fail reporting |
| Scorecard automation | Convert `%APPDATA%` Phase 5C scorecard capture into CI artifact generation |
| Reliability | Eliminate noisy async shutdown warnings from health checks and connector tasks |
| Release docs | Publish release checklist, rollback plan, and operator runbook updates |

## Non-goals

- No major UI redesign
- No new autonomous agent features
- No architecture-layer bypasses that violate `UI -> AppState -> EventBus -> Services -> Repositories -> Storage`

## Exit criteria

| Criterion | Pass condition |
|-----------|----------------|
| Release checklist | Documented and executable end-to-end |
| CI parity | Local and CI gate outcomes are consistent |
| Runtime cleanliness | No recurring shutdown warnings in daily-driver runs |
| Documentation | `README.md` and architecture docs reflect release workflow |

## Initial tasks

1. Define release checklist and tagging policy for production drops.
2. Add CI job to run Phase gate bundle and publish artifacts.
3. Stabilize async service shutdown path to remove noisy pending-task warnings.
4. Add release notes template and upgrade/rollback instructions.

## Validation commands

```powershell
python scripts/verify_phase5c_preflight.py
python scripts/verify_phase5c.py
python scripts/verify_phase5c_telemetry.py
```

Phase 6 extends these with release-specific checks as they are introduced.
