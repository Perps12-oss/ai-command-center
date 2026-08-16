# Constitutional Pre-Flight — UI Constitution gate repair (Task 0)

**Date:** 2026-08-16  
**Task:** Close the 9 `scripts/verify_ui_constitution.py` failures on `main` (Command Center hero/sidebar labels; ops-card timestamp/relative-time). Scoping: **Task 0**, not folded into later tooltip/hierarchy polish.  
**Status:** APPROVED

## Task Description

Wave 1 governance checks run `verify_ui_constitution.py`. On `main` (`864764e`) it fails with 9 violations. Five are sidebar/workspace identity strings that drifted after Mission Control IA shortened labels. Three are stale-path checks: hero action resolution and ops-card timestamps moved into `ui/mission_control/` but the gate still greps only `command_center_view.py`. One is the missing canonical hero title `Command Center` (Phase 11 D5).

This is **not** Stream A–F Gate 4 code. It restores a verification gate that already existed and the last verified workspace names. It does **not** authorize new UI features, tooltip work, or hierarchy redesign.

## Scoping decision (Task 0 vs Task 4)

| Option | Why rejected / accepted |
|--------|-------------------------|
| Fold into Task 4 (tooltips/hierarchy) | Rejected. Tooltip/hierarchy is visual polish. These 9 failures are a **verification vs constitution** mismatch. Mixing them would delay a gate that already fails on `main` and would couple naming/path repair to unrelated UX work on the same files. |
| **Task 0 (this change)** | **Accepted.** Gates go first. Article 0: verification must not redefine requirements; implementation must not silently drop verified labels. Repair the gate and restore D5 / Articles 13–16 sidebar titles **before** any further Command Center polish. |

Task 4 may still edit `command_center_view.py` later. It must not re-break this gate.

## Authorities Reviewed

- `PROJECT_CONSTITUTION_V4.md` — Art. 0 (verification ≠ requirements; zero regression of verified guarantees); Art. X (pre-flight); Inv 1 (UI projects only)
- `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md` — UI isolation; no GUI on this host
- `docs/ARCHITECTURE.md` — ownership flow unchanged
- `docs/UI_CONSTITUTION.md` — Art. 8 Mission Hero / ops grid; Art. 9 Command Center primary workspace; Art. 10 cards require Timestamp; Arts. 13–16 workspace titles (Execution Center, Agent Monitor, Approval Center, Goal Dashboard)
- `docs/PHASE_11_REMEDIATION_AUDIT.md` D5 — hero title canonical **Command Center**
- `docs/governance/IMPLEMENTATION_GUIDE.md` — Queue 1 is Strategic Runtime Program; this is not a new stream ticket
- `ai_command_center/core/contracts.py`, `ai_command_center/core/events/topics.py` — no contract/topic change

## Files Reviewed

- `scripts/verify_ui_constitution.py` (`_check_hero_action`, `_check_ops_cards_timestamp`, `_check_command_center_naming`, workspace sidebar tuples)
- `ai_command_center/ui/views/command_center_view.py` — aliases `_action_button`; no `_resolve_hero_action` / `_format_relative`
- `ai_command_center/ui/mission_control/mission_hero.py` — `_resolve_hero_action`; title currently `Current Mission`
- `ai_command_center/ui/mission_control/kpi_card.py` — `_updated`, `_format_relative`
- `ai_command_center/ui/components/sidebar.py` — `NAV_GROUPS` shortened labels

## Protected Assets Impacted

None. No ExecutionAuthority, World Model, receipts, or EventBus topic changes.

## Sources of Truth Impacted

UI Constitution workspace **names** remain SoT. Mission Control short labels (`Dashboard`, `Execution`, `Agents`, `Approvals`, `Goals`) were not an accepted constitution amendment. They are restored to the last verified titles.

Product chrome `AI Command Center` (window title, tray) is unchanged — D5 distinguished product name from the Command Center **workspace** title.

## Architectural Invariants Impacted

- Inv 1: renderer-only; label/title strings only.
- Inv 11: no second naming SoT — gate + sidebar + hero must match UI Constitution.
- Art. VII: restore a previously passing gate (Phase 11 close-out claimed `verify_ui_constitution` PASS).

## Contracts Impacted

None. No topic, payload, or `contracts.py` version bump.

## Gate Impact Assessment

Not Strategic Runtime Wave 1–6 stream implementation. Unblocks Wave 1 **governance check** hygiene. `verify_ui_constitution.py` is still advisory in CI (not in `.github/workflows`); this repair makes the local/Wave-1 script green again.

## Historical Gate Impact

Does not reopen E00–E13 or Mission Control P1–P8. Does not declare any phase complete (`PHASE_COMPLETION_RULE.md`).

## Regression Risk

Sidebar labels lengthen (e.g. `Approval Center`). Compact/icon-only mode still blanks button text. Search matches both `view_id` and label. Tests that assert substring `"Approvals"` on the approvals nav button must expect `"Approval Center"`.

## Constitutional Status

APPROVED — proceed with Task 0 only.
