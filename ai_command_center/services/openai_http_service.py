"""OpenAI-compatible HTTP client — streaming /v1/chat/completions (F2 M1)."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from typing import Any, Callable

import aiohttp

from ai_command_center.core.context_manager import ContextBundle
from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    APP_ERROR,
    CHAT_CANCELLED,
    CHAT_COMPLETE,
    CHAT_CHUNK,
    CHAT_ERROR,
    CHAT_STARTED,
    LLM_CANCEL,
    LLM_CHUNK,
    LLM_COMPLETE,
    LLM_ERROR,
    LLM_REQUEST,
    OPENAI_STATUS,
    SETTINGS_SNAPSHOT,
    UI_CHAT_CANCEL,
)
from ai_command_center.platform.secret_store import resolve_openai_api_key
from ai_command_center.services.base import BaseService

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_CONNECT_TIMEOUT_S = 10.0
_REQUEST_TIMEOUT_S = 300.0
_HEALTH_CONNECT_TIMEOUT_S = 1.0
_HEALTH_TOTAL_TIMEOUT_S = 2.0
_LOCAL_ASSISTANT_SYSTEM = (
    "You are a desktop command assistant. Answer directly using only the "
    "context provided. Do not tell the user to open a web browser or visit "
    "external websites unless explicitly asked."
)


class OpenAIHttpService(BaseService):
    """OpenAI-compatible API integration — non-blocking stream on asyncio loop.

    Active request state is single-flight per service instance; cancel() targets
    the current asyncio future only.
    """

    name = "openai"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._base_url = _DEFAULT_BASE_URL
        self._api_key = ""
        self._active_provider = "ollama"
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session: aiohttp.ClientSession | None = None
        self._active_request_id: str | None = None
        self._active_future: asyncio.Future[Any] | None = None
        self._health_task: asyncio.Future[Any] | None = None
        self._last_status_key: tuple[bool, bool, str] | None = None
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._start_loop()
        self._session = asyncio.run_coroutine_threadsafe(
            self._create_session(), self._loop
        ).result(timeout=5.0)
        self._unsubscribers.append(
            self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe(UI_CHAT_CANCEL, self._on_cancel_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(LLM_REQUEST, self._on_llm_request)
        )
        self._health_task = asyncio.run_coroutine_threadsafe(
            self._delayed_health_check(), self._loop
        )

    async def _delayed_health_check(self) -> None:
        await asyncio.sleep(1)
        await self._health_check()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self.cancel()
        if self._health_task is not None:
            self._health_task.cancel()
            self._health_task = None
        if self._loop and self._loop.is_running():
            session = self._session
            self._session = None
            shutdown_future = asyncio.run_coroutine_threadsafe(
                self._shutdown_loop(session), self._loop
            )
            try:
                shutdown_future.result(timeout=5.0)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5.0)
        self._loop = None
        self._thread = None

    async def _shutdown_loop(self, session: aiohttp.ClientSession | None) -> None:
        try:
            if session is not None:
                await session.close()
        except Exception:
            pass
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        asyncio.get_running_loop().stop()

    def _on_settings_snapshot(self, event: Event) -> None:
        self._active_provider = str(event.payload.get("provider", "ollama")).strip() or "ollama"
        base = str(event.payload.get("openai_base_url", self._base_url)).strip()
        if base:
            self._base_url = base.rstrip("/")
        stored_key = str(event.payload.get("openai_api_key", ""))
        self._api_key = resolve_openai_api_key(stored_key)

    def _on_cancel_request(self, event: Event) -> None:
        rid = event.payload.get("request_id")
        self.cancel(str(rid) if rid else None)

    def _on_llm_request(self, event: Event) -> None:
        provider = str(event.payload.get("provider", self._active_provider)).strip()
        if provider != "openai":
            return
        bundle = event.payload.get("bundle")
        if not isinstance(bundle, ContextBundle):
            return
        self.stream_chat(
            bundle,
            model=str(event.payload.get("model", "gpt-4o-mini")),
            request_id=str(event.payload.get("request_id", uuid.uuid4().hex)),
        )

    def _start_loop(self) -> None:
        if self._loop is not None:
            return
        ready = threading.Event()

        def runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            ready.set()
            loop.run_forever()
            loop.close()

        self._thread = threading.Thread(target=runner, name="openai-async", daemon=True)
        self._thread.start()
        ready.wait(timeout=5.0)
        if self._loop is None:
            raise RuntimeError("OpenAI asyncio loop failed to start")

    def stream_chat(
        self,
        bundle: ContextBundle,
        *,
        model: str,
        request_id: str | None = None,
    ) -> str:
        if not bundle.prompt:
            raise ValueError("ContextBundle.prompt must not be empty")
        if self._loop is None:
            raise RuntimeError("OpenAI service not loaded")

        rid = request_id or uuid.uuid4().hex
        self._active_request_id = rid
        future = asyncio.run_coroutine_threadsafe(
            self._stream_chat_async(bundle, model, rid),
            self._loop,
        )
        self._active_future = future
        return rid

    def cancel(self, request_id: str | None = None) -> bool:
        if self._active_request_id is None:
            return False
        if request_id is not None and request_id != self._active_request_id:
            return False
        if self._active_future is not None:
            self._active_future.cancel()
            return True
        return False

    async def _create_session(self) -> aiohttp.ClientSession:
        timeout = aiohttp.ClientTimeout(
            total=_REQUEST_TIMEOUT_S,
            connect=_CONNECT_TIMEOUT_S,
        )
        return aiohttp.ClientSession(timeout=timeout)

    async def _health_check(self) -> None:
        health_timeout = aiohttp.ClientTimeout(
            total=_HEALTH_TOTAL_TIMEOUT_S,
            connect=_HEALTH_CONNECT_TIMEOUT_S,
        )
        while True:
            online = False
            detail = ""
            configured = bool(self._api_key)
            if not configured:
                detail = "api key not configured"
            else:
                try:
                    session = self._session
                    if session is None:
                        break
                    async with session.get(
                        f"{self._base_url}/models",
                        headers=self._auth_headers(),
                        timeout=health_timeout,
                    ) as resp:
                        online = resp.status == 200
                        if not online:
                            detail = f"HTTP {resp.status}"
                except aiohttp.ClientConnectorError:
                    detail = "connection refused"
                except asyncio.TimeoutError:
                    detail = "timeout"
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    detail = str(exc)

            status_online = online and configured
            status_key = (status_online, configured, detail)
            if status_key != self._last_status_key:
                self._last_status_key = status_key
                self._bus.publish(
                    OPENAI_STATUS,
                    {
                        "online": status_online,
                        "configured": configured,
                        "detail": detail,
                        "url": self._base_url,
                    },
                    source=self.name,
                )
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _stream_chat_async(
        self,
        bundle: ContextBundle,
        model: str,
        request_id: str,
    ) -> None:
        self._bus.publish(
            CHAT_STARTED,
            {
                "request_id": request_id,
                "model": model,
                "sources": list(bundle.sources),
                "token_estimate": bundle.token_estimate,
                "provider": "openai",
            },
            source=self.name,
        )

        if not self._api_key:
            self._publish_error(
                request_id,
                "OpenAI API key not configured. Set it in Settings.",
            )
            self._active_request_id = None
            self._active_future = None
            return

        full_text: list[str] = []
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": _LOCAL_ASSISTANT_SYSTEM},
                    {"role": "user", "content": bundle.prompt},
                ],
                "stream": True,
            }
            session = self._session
            if session is None:
                raise RuntimeError("OpenAI service not loaded")
            url = f"{self._base_url}/chat/completions"
            async with session.post(
                url, json=payload, headers=self._auth_headers()
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"OpenAI-compatible API returned HTTP {resp.status}: {body[:300]}"
                    )

                async for raw_line in resp.content:
                    if asyncio.current_task() and asyncio.current_task().cancelled():
                        raise asyncio.CancelledError()
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    data = json.loads(data_str)
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    chunk = str(delta.get("content", ""))
                    if chunk:
                        full_text.append(chunk)
                        chunk_payload = {
                            "request_id": request_id,
                            "text": chunk,
                        }
                        self._bus.publish(
                            CHAT_CHUNK,
                            chunk_payload,
                            source=self.name,
                        )
                        self._bus.publish(LLM_CHUNK, chunk_payload, source=self.name)

            text = "".join(full_text)
            complete_payload = {
                "request_id": request_id,
                "text": text,
                "model": model,
                "provider": "openai",
            }
            self._bus.publish(CHAT_COMPLETE, complete_payload, source=self.name)
            self._bus.publish(LLM_COMPLETE, complete_payload, source=self.name)
        except asyncio.CancelledError:
            cancel_payload = {"request_id": request_id}
            self._bus.publish(CHAT_CANCELLED, cancel_payload, source=self.name)
            self._bus.publish(LLM_CANCEL, cancel_payload, source=self.name)
        except aiohttp.ClientConnectorError:
            self._publish_error(
                request_id,
                f"Cannot connect to OpenAI-compatible API at {self._base_url}.",
            )
        except asyncio.TimeoutError:
            self._publish_error(request_id, "OpenAI-compatible request timed out.")
        except json.JSONDecodeError as exc:
            self._publish_error(request_id, f"Invalid OpenAI-compatible response: {exc}")
        except Exception as exc:
            self._publish_error(request_id, str(exc))
        finally:
            self._active_request_id = None
            self._active_future = None

    def _publish_error(self, request_id: str | None, message: str) -> None:
        payload: dict[str, Any] = {"message": message}
        if request_id:
            payload["request_id"] = request_id
        self._bus.publish(CHAT_ERROR, payload, source=self.name)
        self._bus.publish(LLM_ERROR, payload, source=self.name)
        self._bus.publish(APP_ERROR, {"message": message}, source=self.name)
