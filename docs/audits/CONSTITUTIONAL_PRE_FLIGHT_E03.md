# Constitutional Pre-Flight — PR-UI-E03 OS Palette

**Date:** 2026-07-22
**Slice:** PR-UI-E03 — OS Palette
**Baseline:** `origin/main` @ `14e0b31` (post-E02)

## 1. Authority documents read

- [x] `PROJECT_CONSTITUTION_V4.md`
- [x] `docs/UI_CONSTITUTION.md`
- [x] `docs/agents/CURSOR_AUDIT_GATE.md`
- [x] `docs/agents/DEVIN_UI_HANDOVER.md`
- [x] `docs/architecture/adr/ADR-006_EXECUTION_AUTHORITY_CANONICAL.md`
- [x] `docs/architecture/UI_IMPLEMENTATION_ROADMAP_PHASE_B_EVOLUTION.md` (E03 section)

## 2. Scope definition (from roadmap)

**PR-UI-E03 — OS Palette**

- Refactor `CommandPalette` into `OSPalette` with provider-driven sections.
- Keep `Ctrl+K` trigger.
- Static section: navigation, actions, shortcuts.
- Dynamic section: Workspace OS entity commands.
- Provider registry so new providers can register commands.
- Add `UI_PALETTE_ACTION` and `PALETTE_PROVIDER_REGISTER` topics.

**Files to modify**
- `ai_command_center/ui/design_system/command.py`
- `ai_command_center/ui/shell/application_shell.py`
- `ai_command_center/ui/controller.py`
- `ai_command_center/core/events/topics.py`

**Files to create**
- `ai_command_center/ui/design_system/palette_provider.py`
- `tests/ui/test_os_palette.py`

## 3. Architecture check

- UI reads `AppState` through `UIController.snapshot()`.
- UI publishes intents via `EventBus` (`UI_NAVIGATE`, `UI_OPEN_CHAT`, `UI_LAUNCH_RESOURCE`, `UI_COMMAND`, `UI_PALETTE_*`).
- No direct repository/SQLite/Ollama access from UI.
- No OperatorKernel wiring.
- `OSPalette` is a renderer; command execution delegates to existing callbacks/intents.

## 4. Primitive reuse

- Reuse existing `CommandPalette` CTkToplevel shell (no new window class).
- Reuse `UIController` as palette provider registry host.
- Reuse `workspace_os.entities` projection from `AppState`.
- No new graph/timeline/inspector engine.

## 5. AppState / State authority

- No new AppState fields for E03.
- `UIController` holds a local `palette_providers` list (UI-layer registry, not authoritative state).
- Commands are closures that publish existing intents; palette is not SoT.

## 6. Risks / deferrals

- E03 only wires static + Workspace OS providers; plugin/provider registration via `PALETTE_PROVIDER_REGISTER` bus topic is added as a stable extension point but not fully consumed until E05+.
- Keyboard shortcut help (`keyboard_shortcuts_overlay.py`) will be updated in E04 (Navigation Shell), not E03.
- "Clear" on the Global Context Bar (E02 condition #4) remains unwired; will be handled in E04.

## 7. Verification plan

- `python3 -m ruff check ai_command_center`
- `python3 -m pytest tests/ui/`
- `python3 scripts/verify_ui_constitution.py`
- `python3 scripts/verify_constitution.py`
- `python3 scripts/arch_lint.py --baseline tests/arch_lint_baseline.json`
- `python3 tools/ucgs_runner.py` + `python3 tools/ucgs_ci_gate.py .ucgs_last.yaml`

## 8. Pre-flight verdict

**GO** — E03 can be implemented on `origin/main` @ `14e0b31`.
