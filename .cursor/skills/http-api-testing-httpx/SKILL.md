---
name: http-api-testing-httpx
description: Use when testing outbound HTTP with httpx in ai-command-center (Ollama, OpenAI, capability providers). Triggers on: httpx, AsyncClient, pytest-httpx, REST client tests, mock HTTP, or API response assertions. Do not use this to add a product HTTP server.
---

# HTTP API testing with httpx (ACC)

httpx + pytest patterns for **outbound** HTTP. ACC is not a FastAPI/Express app.

## ACC governance deference

Local tooling under `.cursor/skills/` — **not** Level-1/2 authority.

Forbidden by this skill (would be architecture, not a test convenience):

- Adding a product HTTP/REST server or FastAPI `TestClient` surface
- UI or services calling Ollama/OpenAI/httpx directly (UI isolation; Inv 6 —
  AI requests go through `ContextManager`)
- Logging request/response bodies, prompts, or secrets (Inv 9 telemetry firewall)
- Treating an external runtime as system of record (Inv 13)

Integration tests for in-process behavior use **EventBus** topics
(`ai_command_center/core/events/topics.py`) and `tests/support/RecordingEventBus`,
not HTTP.

## When to use httpx in tests

- Runtime/provider adapters that already speak HTTP (Ollama, hosted LLM, ARI
  sidecars).
- Asserting URL, method, headers, timeout, and error mapping.
- Mocking the network so the suite stays deterministic and offline
  (`README_TESTING.md`).

## Preferred style

Use `httpx.AsyncClient` only where production code is async. Prefer injecting a
fake client (see `FakeOllamaClient` in `tests/support`) over hitting the wire.

If you must mock transport:

```python
import httpx
import pytest


class MockTransport(httpx.MockTransport):
    pass


@pytest.fixture
def httpx_client(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "127.0.0.1"
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="http://127.0.0.1:11434") as client:
        yield client
```

Async variant: `httpx.AsyncClient` + `httpx.MockTransport` in an async fixture
(`pytest-asyncio` only if the module already uses it).

## Assertions

- Status code, JSON shape via domain dataclasses — not raw dicts as the
  long-lived contract.
- Timeouts and connection errors map to service `ERROR` / `DEGRADED` and
  `service.error` / `tool.failed` topics, not uncaught exceptions in UI.
- Never assert against live `:11434` in default CI.

## What not to copy from generic API-testing skills

- Supertest / Express / Vitest examples
- `TestClient(app)` against a new ACC HTTP app
- Pact/OpenAPI product APIs (ACC has none as SoT)
- Real credentials or `.env` API tokens in fixtures

## Commands

```bash
APPDATA=/tmp/aicc_appdata python3 -m pytest -m "not slow"
```

Install httpx only if production code already depends on it; do not add a
network stack to satisfy this skill.
