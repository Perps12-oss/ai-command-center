#!/usr/bin/env python3
"""Phase 3B extended audit — architecture, failures, performance (read-only diagnostics)."""

from __future__ import annotations

import asyncio
import json
import socket
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def _mock_chat_ok(_):
    from aiohttp import web

    r = web.StreamResponse(status=200)
    await r.prepare(_)
    for t in ("Hi", " there"):
        await r.write(
            (json.dumps({"message": {"content": t}, "done": False}) + "\n").encode()
        )
        await asyncio.sleep(0.05)
    await r.write((json.dumps({"done": True}) + "\n").encode())
    return r


async def _mock_chat_404(_):
    from aiohttp import web

    return web.Response(status=404, text='{"error":"model not found"}')


async def _mock_chat_bad_json(_):
    from aiohttp import web

    r = web.StreamResponse(status=200)
    await r.prepare(_)
    await r.write(b"not-json\n")
    await r.write((json.dumps({"done": True}) + "\n").encode())
    return r


async def _mock_chat_slow_first(_):
    from aiohttp import web

    r = web.StreamResponse(status=200)
    await r.prepare(_)
    await asyncio.sleep(0.4)
    await r.write(
        (json.dumps({"message": {"content": "late"}, "done": False}) + "\n").encode()
    )
    await r.write((json.dumps({"done": True}) + "\n").encode())
    return r


def _run_server(port: int, route_map: dict) -> threading.Thread:
    from aiohttp import web

    app = web.Application()
    for path, handler in route_map.items():
        app.router.add_post(path, handler)
    app.router.add_get("/api/tags", lambda _: web.json_response({"models": []}))

    loop = asyncio.new_event_loop()

    def serve():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(web._run_app(app, host="127.0.0.1", port=port, print=None))

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    time.sleep(0.35)
    return t


def _wait(events: list, topic: str, timeout=6.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if topic in events:
            return True
        time.sleep(0.02)
    return False


def main() -> int:
    from ai_command_center.core.context_manager import ContextManager
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.services.ollama_http_service import OllamaHttpService

    results: dict[str, object] = {}
    events: list[str] = []
    payloads: dict[str, list] = {}
    bus_times: list[float] = []

    def tap(e):
        events.append(e.topic)
        payloads.setdefault(e.topic, []).append(dict(e.payload))

    bus = EventBus(debug_mode=True)
    bus.subscribe_all(tap)

    def slow_handler(e):
        if e.topic == "chat.chunk":
            time.sleep(0.001)  # simulate subscriber work

    bus.subscribe("chat.chunk", slow_handler)

    svc = OllamaHttpService(bus)
    svc.load()
    port = _free_port()
    _run_server(port, {"/api/chat": _mock_chat_ok})
    bus.publish(
        "settings.snapshot",
        {"ollama_url": f"http://127.0.0.1:{port}", "low_memory_mode": "false"},
        source="audit",
    )
    time.sleep(0.1)

    bundle = ContextManager().build_context("perf test")
    t0 = time.perf_counter()
    rid = svc.stream_chat(bundle, model="m")
    submit_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    while "chat.chunk" not in events and time.time() - t1 < 5:
        time.sleep(0.005)
    first_token_ms = (time.perf_counter() - t1) * 1000 if "chat.chunk" in events else None

    while "chat.complete" not in events and time.time() - t1 < 8:
        time.sleep(0.02)

    # EventBus handler duration probe
    probe_bus = EventBus(debug_mode=True)
    durations: list[float] = []

    def probe(_e):
        durations.append(0.0)

    probe_bus.subscribe("chat.chunk", probe)

    def timed_publish():
        start = time.perf_counter()
        probe_bus.publish("chat.chunk", {"text": "x"}, source="audit")
        bus_times.append((time.perf_counter() - start) * 1000)

    for _ in range(20):
        timed_publish()

    results["submit_latency_ms"] = round(submit_ms, 2)
    results["first_token_latency_ms"] = round(first_token_ms, 2) if first_token_ms else None
    results["eventbus_publish_ms_p99"] = round(sorted(bus_times)[-1], 3)

    # Cancel responsiveness
    events.clear()
    payloads.clear()
    slow_port = _free_port()
    _run_server(slow_port, {"/api/chat": _mock_chat_slow_first})
    bus.publish("settings.snapshot", {"ollama_url": f"http://127.0.0.1:{slow_port}"}, source="audit")
    time.sleep(0.1)
    rid2 = svc.stream_chat(ContextManager().build_context("cancel"), model="m")
    time.sleep(0.05)
    tc = time.perf_counter()
    svc.cancel(rid2)
    cancel_ms = (time.perf_counter() - tc) * 1000
    while "chat.cancelled" not in events and time.perf_counter() - tc < 3:
        time.sleep(0.01)
    results["cancel_call_ms"] = round(cancel_ms, 2)
    results["cancel_to_event_ms"] = round((time.perf_counter() - tc) * 1000, 2) if "chat.cancelled" in events else None

    # Model missing
    events.clear()
    p404 = _free_port()
    _run_server(p404, {"/api/chat": _mock_chat_404})
    bus.publish("settings.snapshot", {"ollama_url": f"http://127.0.0.1:{p404}"}, source="audit")
    time.sleep(0.1)
    svc.stream_chat(ContextManager().build_context("missing model"), model="nope")
    _wait(events, "chat.error")
    err404 = payloads.get("chat.error", [{}])[-1].get("message", "") if events else ""
    results["model_missing_handled"] = "404" in err404 or "not found" in err404.lower() or "HTTP" in err404

    # Malformed JSON
    events.clear()
    payloads.clear()
    pb = _free_port()
    _run_server(pb, {"/api/chat": _mock_chat_bad_json})
    bus.publish("settings.snapshot", {"ollama_url": f"http://127.0.0.1:{pb}"}, source="audit")
    time.sleep(0.1)
    svc.stream_chat(ContextManager().build_context("bad json"), model="m")
    _wait(events, "chat.error")
    bad = payloads.get("chat.error", [{}])[-1].get("message", "")
    results["malformed_handled"] = "Invalid Ollama response" in bad

    # Offline
    events.clear()
    bus.publish("settings.snapshot", {"ollama_url": "http://127.0.0.1:1"}, source="audit")
    svc.stream_chat(ContextManager().build_context("offline"), model="m")
    _wait(events, "chat.error")
    off = payloads.get("chat.error", [{}])[-1].get("message", "")
    results["offline_message"] = off

    svc.unload()

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
