#!/usr/bin/env python3
"""Phase 3B gate — Ollama HTTP streaming, cancel, offline recovery."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def _mock_ollama_chat(request):
    from aiohttp import web

    response = web.StreamResponse(
        status=200,
        headers={"Content-Type": "application/x-ndjson"},
    )
    await response.prepare(request)
    try:
        chunks = ["Hello", " ", "from", " ", "Ollama"]
        for piece in chunks:
            line = json.dumps(
                {"message": {"role": "assistant", "content": piece}, "done": False}
            )
            await response.write((line + "\n").encode())
            await asyncio.sleep(0.08)
        await response.write(
            (json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}) + "\n").encode()
        )
    except (ConnectionError, asyncio.CancelledError):
        pass
    return response


async def _mock_slow_chat(request):
    from aiohttp import web

    response = web.StreamResponse(status=200)
    await response.prepare(request)
    try:
        for i in range(30):
            line = json.dumps(
                {"message": {"role": "assistant", "content": f"{i} "}, "done": False}
            )
            await response.write((line + "\n").encode())
            await asyncio.sleep(0.15)
        await response.write(
            (json.dumps({"done": True}) + "\n").encode()
        )
    except (ConnectionError, asyncio.CancelledError):
        pass
    return response


async def _mock_tags(_request):
    from aiohttp import web

    return web.json_response({"models": []})


async def _mock_generate(_request):
    from aiohttp import web

    return web.json_response({"response": ""})


def _run_mock_server(port: int, slow: bool = False) -> tuple:
    from aiohttp import web

    app = web.Application()
    handler = _mock_slow_chat if slow else _mock_ollama_chat
    app.router.add_post("/api/chat", handler)
    app.router.add_get("/api/tags", _mock_tags)
    app.router.add_post("/api/generate", _mock_generate)

    runner = web.AppRunner(app)
    loop = asyncio.new_event_loop()

    def serve() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", port)
        loop.run_until_complete(site.start())
        loop.run_forever()

    thread = threading.Thread(target=serve, name="mock-ollama", daemon=True)
    thread.start()
    time.sleep(0.3)
    return runner, loop, thread


def _wait_for_topic(topics: list[str], name: str, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if name in topics:
            return True
        time.sleep(0.05)
    return False


def main() -> int:
    print("=== Phase 3B Gate Verification ===")
    failures: list[str] = []

    http_path = PROJECT_ROOT / "ai_command_center" / "services" / "ollama_http_service.py"
    if not http_path.is_file():
        failures.append("ollama_http_service.py missing")
    else:
        src = http_path.read_text(encoding="utf-8")
        for token in ("aiohttp", "ContextBundle", "CHAT_CHUNK", "CHAT_CANCELLED"):
            if token not in src:
                failures.append(f"ollama_http_service.py missing {token}")

    from ai_command_center.application import create_application

    app = create_application(debug_mode=True)
    from ai_command_center.services.ollama_http_service import OllamaHttpService

    ollama = app.services.get("ollama")
    if not isinstance(ollama, OllamaHttpService):
        failures.append("application must register OllamaHttpService")
    app.shutdown()

    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.ollama_http_service import OllamaHttpService

    # --- Streaming against mock server ---
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    _run_mock_server(port, slow=False)

    bus = EventBus(debug_mode=True)
    events: list[str] = []
    payloads: dict[str, dict] = {}

    def tap(event) -> None:
        events.append(event.topic)
        payloads[event.topic] = dict(event.payload)

    bus.subscribe_all(tap)

    service = OllamaHttpService(bus)
    service.load()
    bus.publish(
        "settings.snapshot",
        {
            "ollama_url": f"http://127.0.0.1:{port}",
            "ollama_keep_alive": "10m",
            "low_memory_mode": "false",
        },
        source="test",
    )
    time.sleep(0.2)

    bundle = ContextManager().build_context("Say hi")
    rid = service.stream_chat(bundle, model="test-model")

    if not _wait_for_topic(events, "chat.complete"):
        failures.append("mock stream did not complete")
    else:
        text = str(payloads.get("chat.complete", {}).get("text", ""))
        if "Hello from Ollama" not in text:
            failures.append(f"unexpected stream text: {text!r}")

    # --- Offline recovery ---
    events.clear()
    bus.publish(
        "settings.snapshot",
        {"ollama_url": "http://127.0.0.1:1", "low_memory_mode": "false"},
        source="test",
    )
    rid_off = service.stream_chat(ContextManager().build_context("offline test"), model="x")
    if not _wait_for_topic(events, "chat.error", timeout=8.0):
        failures.append("offline Ollama did not emit chat.error")
    else:
        msg = str(payloads.get("chat.error", {}).get("message", ""))
        if "not running" not in msg.lower() and "refused" not in msg.lower():
            failures.append(f"offline message not user-friendly: {msg!r}")

    if "app.error" not in events:
        failures.append("offline path should publish app.error")

    # --- Cancellation ---
    events.clear()
    slow_port = port + 1
    try:
        s2 = socket.socket()
        s2.bind(("127.0.0.1", 0))
        slow_port = s2.getsockname()[1]
        s2.close()
    except OSError:
        slow_port = port + 1
    _run_mock_server(slow_port, slow=True)
    bus.publish(
        "settings.snapshot",
        {"ollama_url": f"http://127.0.0.1:{slow_port}"},
        source="test",
    )
    time.sleep(0.2)

    rid_slow = service.stream_chat(
        ContextManager().build_context("slow"), model="test-model"
    )
    time.sleep(0.25)
    cancelled = service.cancel(rid_slow)
    if not cancelled:
        failures.append("cancel() returned False during active stream")
    if not _wait_for_topic(events, "chat.cancelled", timeout=6.0):
        failures.append("cancel did not emit chat.cancelled")

    service.unload()

    # --- ContextManager gate still enforced in chat handler ---
    handler_src = (
        PROJECT_ROOT / "ai_command_center" / "services" / "chat_handler_service.py"
    ).read_text(encoding="utf-8")
    if "build_context" not in handler_src:
        failures.append("chat_handler must still use ContextManager")

    if failures:
        print("FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS: Phase 3B — Ollama HTTP streaming, cancel, offline recovery")
    print(f"  stream request_id: {rid}")
    print(f"  offline request_id: {rid_off}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
