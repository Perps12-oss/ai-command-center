# AI Command Center

Local AI command surface for **Windows ARM64** — canonical repository.

## Project home

`c:\Users\S8633\Documents\GITHUB\ai-command-center` (canonical)

Legacy OneDrive copy is kept as a read-only backup until the unified app is proven stable.

## Target hardware

- Lenovo 83N3, Snapdragon X, 16 GB RAM
- **Native ARM64 Python required** — the default `python` on PATH may be x64-emulated (`platform.machine()` reports `AMD64`).

Recommended interpreter:

```powershell
C:\Users\S8633\AppData\Local\Python\bin\python.exe
```

Runtime application data (not in repo): `%APPDATA%\AICommandCenter`

## Setup

```powershell
cd c:\Users\S8633\Documents\GITHUB\ai-command-center
C:\Users\S8633\AppData\Local\Python\bin\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
python scripts\preflight_arm64.py
```

## Stage 1 — Unified UI

```powershell
C:\Users\S8633\AppData\Local\Python\bin\python.exe scripts\verify_phase1.py
C:\Users\S8633\AppData\Local\Python\bin\python.exe main.py
```

- **Alt+Space** — official global hotkey to toggle command palette
- **Ctrl+Shift+W** — Workspace OS Inspector
- **System tray** — Open / Exit; status color by phase
- **Glass shell** — sidebar, command box, unified views (Home, Chat, Notes, Memory, System, Plugins, Settings)
- **Transparency slider** — Settings → Appearance → Window opacity
- UI uses **EventBus + AppState only** (see `docs/ARCHITECTURE.md`)

## Phase 1 — Core infrastructure

```powershell
C:\Users\S8633\AppData\Local\Python\bin\python.exe scripts\verify_phase1.py
```

Architecture: `Services → Events → AppState → UI`.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for repository policy, state ownership, and EventBus rules.

**Phase 3:** [docs/PHASE3.md](docs/PHASE3.md) — scope, build order, review gates. Run `scripts/verify_context_manager.py` before Ollama code.

| Module | Role |
|--------|------|
| `core/event_bus.py` | Thread-safe pub/sub |
| `core/app_state.py` | Immutable snapshots + reducers |
| `core/service_manager.py` | `load()` / `hibernate()` / `unload()` |
| `services/base.py` | Service lifecycle contract |
| `db/schema.sql` | SQLite + FTS5 + V2 hooks |
| `application.py` | Bootstrap without UI |

Database: `%APPDATA%\AICommandCenter\app.db`

## Phase 0 gate

```powershell
# 1. Log baseline RAM + startup timing
C:\Users\S8633\AppData\Local\Python\bin\python.exe scripts\benchmark_startup.py

# 2. Run fail-by-default preflight (requires baseline.json)
C:\Users\S8633\AppData\Local\Python\bin\python.exe scripts\preflight_arm64.py
```

Baseline log: `%APPDATA%\AICommandCenter\baseline.json`

See [compatibility_matrix.md](compatibility_matrix.md) for ARM64 vs emulated wheel policy.

## Phase 0 layout

- `scripts/preflight_arm64.py` — fail-by-default environment gate
- `scripts/benchmark_startup.py` — baseline RAM + import timing → `baseline.json`
- `ai_command_center/platform/detector.py` — ARM64, RAM, Ollama PE validation
- `ai_command_center/platform/wheel_audit.py` — dependency tier + wheel arch audit
- `compatibility_matrix.md` — tracked package compatibility
- `main.py` — entry stub (Phase 1+)

## GitHub

Authenticated `gh` users can publish with:

```powershell
gh repo create ai-command-center --private --source=. --remote=origin --push
```

## UCGS v5 governance

Architecture governance kit (warn mode by default).

```powershell
python tools/ucgs_runner.py
python tools/ucgs_ci_gate.py .ucgs_last.yaml
```

Pre-commit hook installed via `ucgs-init.py`. Config: `ucgs.config.yaml`. See `docs/PHASE_LEDGER.md` for phase verdicts.
