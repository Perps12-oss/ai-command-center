# Program 4 Gate Status

**Status:** gated until Program 3 adoption is verified.

Program 4 may not expand platform capabilities until:

1. Program 1 stabilization gates pass.
2. Program 2 local/CI enforcement remains active.
3. Program 3 reports workspace-scoped adoption at or above the transition-plan midpoint.

## Allowed after Program 3 midpoint

| Capability | Allowed scope |
|------------|---------------|
| Model tiers | Settings-backed tier map and workspace task hints through `ModelRouterService` |
| Platform paths | OS-specific runtime directories behind `platform/` abstractions |
| Tool workflows | Tool-only workflow persistence and AppState projection |
| Plugin canvas entities | Publish plugin catalog items into Workspace OS entity topics |
| Large context | Entity graph assembly through EventBus before `ContextManager.build_context()` |

## Still gated after midpoint

| Capability | Gate |
|------------|------|
| Semantic/vector memory | Constitutional amendment plus UCGS profile update |
| Multi-agent runtime expansion | Appendix C sign-off in `ARCHITECTURE_TRANSITION_PLAN.md` |
| Agent workflow steps | Appendix C plus workflow contract review |
| Remote plugin marketplace/code loading | Plugin Runtime architectural review |
| Distributed/cloud execution | New cloud execution contract |

## Prepared code homes

| Module | Purpose |
|--------|---------|
| `ai_command_center.core.state.model_state` | Future `model.selected` AppState projection |
| `ai_command_center.core.state.tool_state` | Future `recent_tool_runs` AppState projection |

These modules are intentionally empty until Program 4 gates are satisfied.
