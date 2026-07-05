"""QwenPaw sidecar lifecycle and REST/SSE bridge (ARI Phase 2)."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any

import aiohttp

from ai_command_center.core.capability_external_registry import clear_external_request
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    CAPABILITY_COMPLETE,
    CAPABILITY_ERROR,
    CAPABILITY_RUNTIME_REQUEST,
    CAPABILITY_STREAM,
    CHAT_COMPLETE,
    CHAT_ERROR,
    CHAT_CHUNK,
    CHAT_STARTED,
    SETTINGS_SNAPSHOT,
)
from ai_command_center.runtime.providers.qwenpaw_health import QwenPawSidecarHealthState
from ai_command_center.runtime.qwenpaw_sse import QwenPawStreamStatus, parse_sse_data_line
from ai_command_center.services.base import BaseService

_logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://127.0.0.1:8088"
_CONNECT_TIMEOUT_S = 5.0
_REQUEST_TIMEOUT_S = 300.0
_HEALTH_INTERVAL_S = 15.0


class QwenPawSidecarService(BaseService):
    """Spawns optional local sidecar and streams ``/api/console/chat`` to the bus."""

    name = "qwenpaw_sidecar"

    def __init__(
        self,
        bus,
        *,
        health_state: QwenPawSidecarHealthState | None = None,
    ) -> None:
        super().__init__(bus)
        self._health_state = health_state or QwenPawSidecarHealthState()
        self._base_url = _DEFAULT_URL
        self._agent_id = "default"
        self._enabled = False
        self._auto_start = False
        self._python_path = ""
        self._auth_token = ""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session: aiohttp.ClientSession | None = None
        self._process: subprocess.Popen[str] | None = None
        self._health_task: asyncio.Future[Any] | None = None
        self._unsubscribers: list[Callable[[], None]] = []

    @property
    def health_state(self) -> QwenPawSidecarHealthState:
        return self._health_state

    def _on_load(self) -> None:
        self._start_loop()
        self._session = asyncio.run_coroutine_threadsafe(
            self._create_session(), self._loop
        ).result(timeout=5.0)
        self._unsubscribers.append(
            self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe(CAPABILITY_RUNTIME_REQUEST, self._on_runtime_request)
        )
        self._health_task = asyncio.run_coroutine_threadsafe(
            self._health_loop(), self._loop
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        if self._health_task is not None:
            self._health_task.cancel()
            self._health_task = None
        if self._loop and self._loop.is_running():
            session = self._session
            self._session = None
            asyncio.run_coroutine_threadsafe(
                self._shutdown_session(session), self._loop
            ).result(timeout=5.0)
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self._loop = None
        self._stop_process()

    def _on_settings_snapshot(self, event: Event) -> None:
        payload = event.payload
        self._enabled = bool(payload.get("qwenpaw_enabled", False))
        self._auto_start = bool(payload.get("qwenpaw_auto_start", False))
        self._base_url = str(payload.get("qwenpaw_url", _DEFAULT_URL)).strip() or _DEFAULT_URL
        self._agent_id = str(payload.get("qwenpaw_agent_id", "default")).strip() or "default"
        self._python_path = str(payload.get("qwenpaw_python", "")).strip()
        self._auth_token = str(payload.get("qwenpaw_auth_token", "")).strip()
        self._health_state.update(
            enabled=self._enabled,
            auto_start=self._auto_start,
            detail="QwenPaw sidecar disabled" if not self._enabled else "Checking sidecar…",
        )
        if self._enabled and self._auto_start and self._python_path:
            self._ensure_process()
        elif not self._enabled:
            self._stop_process()
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._check_health_once(), self._loop)

    def _on_runtime_request(self, event: Event) -> None:
        if event.source != "qwenpaw":
            return
        if not self._enabled:
            self._publish_error(
                str(event.payload.get("request_id", "")),
                "QwenPaw sidecar disabled in settings",
            )
            return
        _, reachable, detail = self._health_state.snapshot()
        if not reachable:
            self._publish_error(
                str(event.payload.get("request_id", "")),
                detail or "QwenPaw sidecar unreachable",
            )
            return
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._stream_chat(dict(event.payload)), self._loop
        )

    def _publish_error(self, request_id: str, message: str) -> None:
        if not request_id:
            return
        payload = {
            "request_id": request_id,
            "provider_id": "qwenpaw",
            "message": message,
        }
        self._bus.publish(CAPABILITY_ERROR, payload, source=self.name)
        self._bus.publish(CHAT_ERROR, {"message": message, "request_id": request_id}, source=self.name)
        clear_external_request(request_id)

    def _start_loop(self) -> None:
        if self._loop is not None:
            return

        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.run_forever()

        self._thread = threading.Thread(target=_run, name="qwenpaw-sidecar", daemon=True)
        self._thread.start()
        for _ in range(100):
            if self._loop is not None:
                break
            threading.Event().wait(0.01)

    async def _create_session(self) -> aiohttp.ClientSession:
        timeout = aiohttp.ClientTimeout(
            total=_REQUEST_TIMEOUT_S,
            connect=_CONNECT_TIMEOUT_S,
        )
        return aiohttp.ClientSession(timeout=timeout)

    async def _shutdown_session(self, session: aiohttp.ClientSession | None) -> None:
        if session is not None and not session.closed:
            await session.close()

    async def _health_loop(self) -> None:
        while True:
            try:
                await self._check_health_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _logger.debug("qwenpaw health loop error: %s", exc)
            await asyncio.sleep(_HEALTH_INTERVAL_S)

    async def _check_health_once(self) -> None:
        if not self._enabled:
            self._health_state.update(reachable=False, detail="QwenPaw sidecar disabled")
            return
        session = self._session
        if session is None:
            self._health_state.update(reachable=False, detail="Sidecar client not ready")
            return
        url = self._base_url.rstrip("/")
        try:
            async with session.get(url, allow_redirects=True) as resp:
                reachable = resp.status < 500
                detail = "Sidecar ready" if reachable else f"Sidecar HTTP {resp.status}"
        except aiohttp.ClientError as exc:
            reachable = False
            detail = f"Sidecar unreachable: {exc}"
        self._health_state.update(reachable=reachable, detail=detail)

    def _ensure_process(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        if not self._python_path:
            return
        cmd = [self._python_path, "-m", "qwenpaw", "app"]
        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            _logger.info("qwenpaw sidecar spawned pid=%s", self._process.pid)
        except OSError as exc:
            _logger.warning("qwenpaw sidecar spawn failed: %s", exc)
            self._health_state.update(reachable=False, detail=f"Spawn failed: {exc}")

    def _stop_process(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None

    async def _stream_chat(self, payload: dict[str, object]) -> None:
        request_id = str(payload.get("request_id", "")).strip()
        query = str(payload.get("query", "")).strip()
        session_id = str(payload.get("session_id", request_id)).strip() or request_id
        kind = str(payload.get("kind", "chat")).strip()
        if not request_id or not query:
            return

        context = payload.get("context_bundle")
        if isinstance(context, dict):
            context_text = str(context.get("prompt", "")).strip()
            if context_text and context_text not in query:
                query = f"{context_text}\n\nUser: {query}"

        self._bus.publish(
            CHAT_STARTED,
            {
                "request_id": request_id,
                "model": f"qwenpaw:{self._agent_id}",
                "sources": ["qwenpaw_sidecar"],
                "token_estimate": len(query.split()),
            },
            source=self.name,
        )

        headers = {
            "Content-Type": "application/json",
            "X-Agent-Id": self._agent_id,
        }
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"

        body = {
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": query}],
                }
            ],
            "session_id": session_id,
            "user_id": "acc-host",
            "channel": "console",
        }

        session = self._session
        if session is None:
            self._publish_error(request_id, "Sidecar HTTP client not ready")
            return

        previous_text = ""
        full_text = ""
        try:
            async with session.post(
                f"{self._base_url.rstrip('/')}/api/console/chat",
                headers=headers,
                json=body,
            ) as resp:
                if resp.status != 200:
                    body_text = await resp.text()
                    raise RuntimeError(
                        f"QwenPaw HTTP {resp.status}: {body_text[:300]}"
                    )

                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8", errors="replace")
                    event = parse_sse_data_line(line, previous_text=previous_text)
                    if event is None:
                        continue
                    if event.assistant_text:
                        previous_text = event.assistant_text
                        full_text = event.assistant_text
                    if event.delta:
                        chunk_payload = {
                            "request_id": request_id,
                            "chunk": event.delta,
                            "text": event.delta,
                            "kind": kind,
                            "provider_id": "qwenpaw",
                        }
                        self._bus.publish(CAPABILITY_STREAM, chunk_payload, source=self.name)
                        self._bus.publish(
                            CHAT_CHUNK,
                            {"request_id": request_id, "text": event.delta},
                            source=self.name,
                        )
                    if event.error_message:
                        raise RuntimeError(event.error_message)
                    if event.status == QwenPawStreamStatus.FAILED:
                        raise RuntimeError(event.error_message or "QwenPaw stream failed")
                    if event.status == QwenPawStreamStatus.COMPLETED:
                        break

            complete_payload = {
                "request_id": request_id,
                "text": full_text,
                "kind": kind,
                "provider_id": "qwenpaw",
                "metadata": {"session_id": session_id, "agent_id": self._agent_id},
            }
            self._bus.publish(CAPABILITY_COMPLETE, complete_payload, source=self.name)
            self._bus.publish(
                CHAT_COMPLETE,
                {
                    "request_id": request_id,
                    "text": full_text,
                    "model": f"qwenpaw:{self._agent_id}",
                },
                source=self.name,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _logger.warning("qwenpaw stream failed request_id=%s: %s", request_id, exc)
            self._publish_error(request_id, str(exc))
        finally:
            clear_external_request(request_id)
