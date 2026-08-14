---
name: pytest
description: Use when writing, running, or debugging pytest in ai-command-center. Triggers on: pytest, fixtures, parametrize, markers, coverage, conftest, failing tests, or python -m pytest.
---

# Pytest (ACC)

Project pytest conventions for `ai-command-center`. Invoke `/pytest` or apply
when tests are the task.

## ACC governance deference

Local tooling under `.cursor/skills/` — **not** Level-1/2 authority. Higher
authority wins: `PROJECT_CONSTITUTION_V4.md` → `AGENTS.md` /
`docs/ARCHITECTURE_ENFORCEMENT.md` → architecture + contracts → **Accepted**
ADRs → `origin/main`.

Canonical how-to: `README_TESTING.md` and `pytest.ini`.

## How to run (this repo)

Use `python3 -m pytest` (Cloud/Linux). Console scripts may not be on `PATH`.

```bash
APPDATA=/tmp/aicc_appdata python3 -m pytest -m "not slow"
APPDATA=/tmp/aicc_appdata python3 -m pytest tests/test_eventbus_concurrency.py -v
APPDATA=/tmp/aicc_appdata python3 -m pytest tests/path/test_file.py::test_name
```

Coverage is on by default (`pytest.ini` → pytest-cov). Fast subset: `-m "not slow"`.
Five Windows/ARM64 tests skip on this host.

Do **not** use `uv run pytest` unless the repo is uv-managed (it is not).

## Layout

- Tests live in `tests/` mirroring risk areas, not a 1:1 package clone of every module.
- Shared fixtures/mocks: `tests/support/` (`RecordingEventBus`, `FakeOllamaClient`,
  `StubLifecycleService`, `CommandSandbox`).
- Markers: `slow`, `windows`, `arm64`, `security`, `control_plane_acceptance`,
  `orchestration`. `--strict-markers` is on.

## Fixtures and isolation

- Narrowest fixture scope that is correct (`function` default).
- No shared mutable session state. No real network. No live Ollama/OpenAI/vault.
- Headless core needs `APPDATA` (`get_runtime_data_dir()`). Set it in tests or the
  command line; do not invent `GLOBAL_*` state.
- Prefer `tmp_path` for files. Repositories own storage in product code; tests
  use temp dirs / fakes, never the operator's real `%APPDATA%`.

## Assertions

- Plain `assert` (pytest rewrite). `pytest.raises(..., match=...)` for errors.
- Assert on EventBus topics, `AppState` snapshots, and domain dataclasses — not
  on UI widgets doing business logic.
- Do not weaken CI, coverage floors, arch_lint baselines, or bandit baselines
  to go green.

## Parametrize and mocks

- `@pytest.mark.parametrize` with `ids=` for readable failures.
- Mock HTTP at the client boundary (`httpx` / Ollama stub). See
  `http-api-testing-httpx` for outbound HTTP. Do not stand up FastAPI as a
  product surface.
- Prefer existing `tests/support` fakes over ad-hoc `unittest.mock` of internals.

## Pitfalls (ACC-specific)

- GUI (`main.py`) is Windows-ARM64 only; do not write tests that launch Tk on
  Linux Cloud.
- Do not add polling ≤100 ms (Art. XVII). Event-driven tests only.
- Do not import deprecated shims. Do not call services from other services in
  new tests as if that were allowed.
- Timeout is 120s per test (`pytest.ini`). Soak tests are `slow`.

## When tests fail

1. Read the short traceback (`--tb=short` is fine for iteration).
2. Fix product code or the test — never skip an invariant.
3. Re-run the failing node id, then `-m "not slow"` before claiming green.
