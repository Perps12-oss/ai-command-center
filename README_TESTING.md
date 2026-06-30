# Testing Guide — AI Command Center

A self-contained `pytest` suite that stress-tests and validates the application
against five risk areas. Every test is deterministic and network-free (Ollama,
HTTP and the filesystem are mocked or sandboxed), so the suite runs the same on a
native **Windows ARM64** box and on hosted x64 CI runners.

> Platform-specific tests (the live ARM64 binary gate, the emulation/subprocess
> checks) **skip automatically** when they are not applicable, so the suite is
> always green on the right hardware and never produces false failures elsewhere.

## Contents

| Path | Purpose |
|------|---------|
| `pytest.ini` | Test config, markers, coverage, per-test timeout |
| `requirements-test.txt` | Test/CI tooling (pytest, pytest-cov, bandit, pefile, psutil, …) |
| `tests/support/` | Reusable mocks: `RecordingEventBus`, `FakeOllamaClient`, `StubLifecycleService`, `CommandSandbox`, `run_with_timeout`, `CountdownLatch` |
| `scripts/check_arm64_binaries.py` | Risk #1 — PE machine-type scanner |
| `scripts/arch_lint.py` | Risk #2 — AST architecture linter |
| `.bandit` + `tests/bandit_baseline.json` | Risk #3 — security scan config + ratchet baseline |
| `tests/arch_lint_baseline.json` | Risk #2 — accepted-violations baseline |
| `.github/workflows/tests.yml` | CI — portable suite (Windows + Linux) |
| `.github/workflows/arm64-gate.yml` | CI — hard native-ARM64 gate |
| `azure-pipelines-tests.yml` | Azure DevOps pipeline |

## Quick start

```powershell
# from the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # (Linux/macOS: source .venv/bin/activate)
python -m pip install -U pip
pip install -r requirements-test.txt

# run everything (incl. slow soak/chaos) with coverage
python -m pytest

# fast run — skip the long soak/chaos tests
python -m pytest -m "not slow"

# only one risk area
python -m pytest tests/test_eventbus_concurrency.py -v
```

Coverage (term + XML) is produced automatically via `pytest-cov` (configured in
`pytest.ini`). The XML report is written to `coverage.xml`.

### Markers

| Marker | Meaning |
|--------|---------|
| `slow` | long-running soak/chaos tests — deselect with `-m "not slow"` |
| `windows` | needs a real Windows host (skipped elsewhere) |
| `arm64` | needs native Windows ARM64 (skipped on x64 / emulated) |
| `security` | prompt-injection / sandbox / path-traversal tests |

### Tunable environment variables

| Variable | Default | Used by |
|----------|---------|---------|
| `AICC_SOAK_SECONDS` | `6` | `test_memory_soak.py` (set `1800` for the full 30-min soak) |
| `AICC_SOAK_MAX_GROWTH_MB` | `50` | soak RSS-growth threshold |
| `AICC_INDEX_NOTE_COUNT` | `1000` | `test_indexing_tracemalloc.py` vault size |
| `AICC_INDEX_PEAK_LIMIT_MB` | `500` | tracemalloc peak limit |
| `AICC_CHAOS_SECONDS` | `3` | `test_service_lifecycle_chaos.py` duration |

## The five risk areas

### 1. Platform blind spots (ARM64 vs x64)

* **`scripts/check_arm64_binaries.py`** walks the interpreter prefix + every
  `site-packages` dir and reads the PE machine type of every `.exe`/`.dll`/`.pyd`
  (via `pefile`, falling back to a raw header parse). Any non-`IMAGE_FILE_MACHINE_ARM64`
  (`0xAA64`) binary is listed and the script exits non-zero.
  ```powershell
  python scripts/check_arm64_binaries.py            # scan current env
  python scripts/check_arm64_binaries.py --json      # machine-readable
  python scripts/check_arm64_binaries.py --allow legacy.dll
  ```
* **`tests/test_arm64_binaries.py`** validates the scanner with crafted PE
  headers (runs anywhere) and includes a live `@arm64` gate.
* **`tests/test_arm64_emulation_smoke.py`** runs a headless end-to-end chat smoke
  (EventBus → AppState → stub Ollama) and, on Windows, attempts to disable x64
  emulation via `SetProcessMachineTypeToEmulate` then asserts no subprocess of a
  different architecture was spawned (`psutil`).

### 2. Concurrency & state violations

* **`scripts/arch_lint.py`** — AST linter enforcing: R1 no `ui/` → `services/`
  imports, R2 no service instantiation outside `services/` or a composition root,
  R3 no `AppState` attribute assignment outside the `app_state` module. Runs as a
  *ratchet* against `tests/arch_lint_baseline.json` so only **new** violations
  fail.
  ```powershell
  python scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
  # refresh the baseline after an intentional, reviewed change:
  python scripts/arch_lint.py --baseline tests/arch_lint_baseline.json --write-baseline
  ```
* **`tests/test_architecture_lint.py`** — linter logic on synthetic sources + a
  repo-wide ratchet test.
* **`tests/test_state_immutability.py`** — direct `AppState` mutation raises;
  state changes only through reducer events.
* **`tests/test_eventbus_concurrency.py`** — 16 threads × 250 events confirm no
  event is lost, duplicated or corrupted, plus concurrent subscribe/publish.

### 3. Sandboxed shell execution & prompt injection

* **`.bandit`** flags `shell=True`, `eval`, `exec`, `os.system`, `subprocess`
  start helpers, etc. Run on NEW high-severity findings:
  ```powershell
  bandit -r ai_command_center --ini .bandit --baseline tests/bandit_baseline.json --severity-level high
  ```
* **`tests/test_prompt_injection_sandbox.py`** feeds a corpus of adversarial
  `FakeOllamaClient` completions (`rm -rf /`, `& del /f /s C:\*`, `; calc.exe`, …)
  through the reference `CommandSandbox` and asserts each is rejected with
  `SecurityError` **before** any subprocess is spawned.
* **`tests/test_path_traversal.py`** — `../../../../Windows/System32/config` style
  paths are refused by the vault repository and the sandbox.

### 4. Memory leaks (SQLite & local indexes)

* **`tests/test_memory_soak.py`** (`slow`) — simulated session sampling RSS with
  `psutil`; asserts net growth `< 50 MB` after `gc.collect()`.
* **`tests/test_sqlite_connection_cleanup.py`** — many single- and multi-threaded
  connections all close (open-count returns to 0); closed connections are
  unusable.
* **`tests/test_indexing_tracemalloc.py`** — indexes 1000 mock notes into real
  SQLite FTS under `tracemalloc`; asserts peak `< 500 MB` and that bodies are
  released afterwards.

### 5. OS-level lifecycle deadlocks (ServiceManager)

* **`tests/test_service_lifecycle_chaos.py`** (`slow`) — background workers
  hammer `load`/`unload` while a main-thread heartbeat proves the UI loop never
  stalls beyond a small bound.
* **`tests/test_service_unload_timeout.py`** — a hung `unload` is detected via the
  `run_with_timeout` watchdog (raises `TimeoutError`) without freezing the caller;
  the offending service is observably stuck in `STOPPING`.
* **`tests/test_service_resource_lock.py`** — a service holding an exclusive OS
  file lock releases it on unload; a hung teardown keeps the lock (the leak the
  watchdog is meant to surface) until force-released.

## Pre-commit integration

Hooks are defined in `.pre-commit-config.yaml`:

```powershell
pip install pre-commit
pre-commit install
pre-commit run --all-files        # run every hook now
```

Added hooks: `arm64-binary-scan` (risk #1), `arch-lint` (risk #2), `bandit`
(risk #3). The constitution hook is preserved.

> **Note (risk #1 hook on mixed machines):** `arm64-binary-scan` fails by design
> if the active environment contains x64 binaries. On the native ARM64 target it
> passes; if you commit from an x64 box, run it against an ARM64 venv or
> `--allow` known-good files.

## CI integration

### GitHub Actions

* **`.github/workflows/tests.yml`** — runs the portable suite on
  `windows-latest` + `ubuntu-latest` (Python 3.11 & 3.12): arch lint, bandit
  (baseline), full `pytest` with coverage. The ARM64 binary scan runs
  *informational* here (x64 runners can't pass a hard gate).
* **`.github/workflows/arm64-gate.yml`** — the **hard** native-ARM64 gate
  (`runs-on: windows-11-arm` or a self-hosted ARM64 runner). Triggered via
  `workflow_dispatch`; uncomment the `pull_request`/`push` triggers once an
  ARM64 runner is available to gate every PR.

### Azure Pipelines

`azure-pipelines-tests.yml` mirrors the above: a `PortableSuite` stage on hosted
Windows and an `ARM64Gate` stage that requires a self-hosted ARM64 agent pool
named `ARM64-Windows`.

## Known gaps surfaced by the suite

These are **real findings** the suite intentionally tracks (not test bugs):

1. **`ai_command_center/ui/components/hero_panel.py`** imports and instantiates
   `AssetService` directly — a UI→services boundary violation (risk #2). Captured
   in `tests/arch_lint_baseline.json`; remove it by routing asset access through
   the EventBus/AppState and delete the baseline entries.
2. **`tool_executor_service.py`** and **`core/workspace_os_actions.py`** run
   `subprocess.run(..., shell=True)` on un-validated input (risk #3). Captured in
   `tests/bandit_baseline.json` and asserted by the `xfail` test
   `test_production_pipeline_should_refuse_dangerous_command`. Promote
   `tests/support/sandbox.py::CommandSandbox` into `ToolExecutorService` to close
   the gap (the xfail will then xpass — flip it to a normal assertion).
