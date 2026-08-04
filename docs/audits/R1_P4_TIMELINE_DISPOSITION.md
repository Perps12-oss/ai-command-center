# R1 P4 — Timeline stack disposition

**Date:** 2026-08-04  
**Branch:** `cursor/r1-p4-timeline-disposition-6855`  
**Baseline:** `origin/main` @ `eca4a15` (#138 inspector rail)

## Decision

**Accepted:** Mission Control `ActivityTimeline` remains a **secondary multi-domain
activity feed**. It is **not** a parallel execution-timeline engine.

Canonical execution timeline stack stays:

```text
TimelineRenderer → ExecutionTimelineDock
```

(used by Operations, Executions, Agents `RunTimeline`, Workflow, Mission Control
advanced dock).

## Why not compose ActivityTimeline onto TimelineRenderer

| Surface | Shape | Data |
|---------|-------|------|
| `ActivityTimeline` | Vertical GlassCard feed | World mutations, executions, approvals, goals, agents, planner |
| `TimelineRenderer` / dock | Horizontal step scrubber | Ordered `{name, status, duration_ms}` execution steps |

Forcing the feed through the scrubber primitive would be a UX redesign, not a
compose. Mission Control already mounts **both**: mid-band feed + advanced
`ExecutionTimelineDock`.

## R1.4 criterion reading

“One timeline stack” means **one execution scrubber engine** — not “every
chronological list must use TimelineRenderer.”

Canon (`REPOSITORY_TRUTH_CANON.md`): Timeline → `TimelineRenderer` +
`ExecutionTimelineDock` (no parallel **`run_timeline` engine**).

## Hygiene in this PR

- Mission Control `_render_exec_dock` uses `name` (not `label`) so dock tiles
  match `TimelineRenderer`’s contract.
- Docs close the residual checkbox.

## Out of scope / gated

- Redesigning Mission Control mid-band into a second scrubber
- Extending TimelineRenderer into a general activity widget
- Async EventBus, Goose, SA.mutate non-WM, OperatorKernel rewire

## Verdict

**R1.4 timeline residual CLOSED** by disposition (keep feed; one scrubber stack).
