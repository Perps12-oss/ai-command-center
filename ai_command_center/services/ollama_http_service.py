"""Ollama HTTP client — streaming /api/chat on a background asyncio loop (Phase 3B)."""

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
    LLM_REQUEST,
    OLLAMA_STATUS,
    SETTINGS_SNAPSHOT,
    UI_CHAT_CANCEL,
)
from ai_command_center.services.ollama_service import OllamaServiceBase

_DEFAULT_URL = "http://localhost:11434"
_DEFAULT_KEEP_ALIVE = "10m"
_LOW_MEMORY_KEEP_ALIVE = "2m"
_CONNECT_TIMEOUT_S = 5.0
_REQUEST_TIMEOUT_S = 300.0
_LOCAL_ASSISTANT_SYSTEM = (
    "You are a local desktop command assistant. Answer directly using only the "
    "context provided. Do not tell the user to open a web browser, search Google, "
    "or visit external websites."
)


class OllamaHttpService(OllamaServiceBase):
    """Real Ollama integration — non-blocking stream_chat, asyncio cancellation."""

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._base_url = _DEFAULT_URL
        self._keep_alive = _DEFAULT_KEEP_ALIVE
        self._low_memory = False
        self._loaded_model: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._active_request_id: str | None = None
        self._active_future: asyncio.Future[Any] | None = None
        self._unsubscribers: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._start_loop()
        self._unsubscribers.append(
            self._bus.subscribe(SETTINGS_SNAPSHOT, self._on_settings_snapshot)
        )
        self._unsubscribers.append(
            self._bus.subscribe(UI_CHAT_CANCEL, self._on_cancel_request)
        )
        self._unsubscribers.append(
            self._bus.subscribe(LLM_REQUEST, self._on_llm_request)
        )
        asyncio.run_coroutine_threadsafe(self._health_check(), self._loop)

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self.cancel()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=3.0)
        self._loop = None
        self._thread = None

    def _on_settings_snapshot(self, event: Event) -> None:
        self._base_url = str(event.payload.get("ollama_url", self._base_url)).rstrip("/")
        self._keep_alive = str(
            event.payload.get("ollama_keep_alive", self._keep_alive)
        )
        self._low_memory = str(
            event.payload.get("low_memory_mode", "false")
        ).lower() in {"1", "true", "yes"}

    def _on_cancel_request(self, event: Event) -> None:
        rid = event.payload.get("request_id")
        self.cancel(str(rid) if rid else None)

    def _on_llm_request(self, event: Event) -> None:
        bundle = event.payload.get("bundle")
        if not isinstance(bundle, ContextBundle):
            return
        self.stream_chat(
            bundle,
            model=str(event.payload.get("model", "llama3.2:3b")),
            request_id=str(event.payload.get("request_id", uuid.uuid4().hex)),
        )

    def _effective_keep_alive(self) -> str:
        if self._low_memory:
            return _LOW_MEMORY_KEEP_ALIVE
        return self._keep_alive

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

        self._thread = threading.Thread(target=runner, name="ollama-async", daemon=True)
        self._thread.start()
        ready.wait(timeout=5.0)
        if self._loop is None:
            raise RuntimeError("Ollama asyncio loop failed to start")

    def load_model(self, model: str) -> None:
        if self._loop is None:
            raise RuntimeError("Ollama service not loaded")
        asyncio.run_coroutine_threadsafe(
            self._load_model_async(model), self._loop
        )

    def unload_model(self) -> None:
        if self._loop is None or not self._loaded_model:
            return
        model = self._loaded_model
        asyncio.run_coroutine_threadsafe(
            self._unload_model_async(model), self._loop
        )

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
            raise RuntimeError("Ollama service not loaded")

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

    async def _health_check(self) -> None:
        online = False
        detail = ""
        try:
            timeout = aiohttp.ClientTimeout(total=_CONNECT_TIMEOUT_S)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self._base_url}/api/tags") as resp:
                    online = resp.status == 200
                    if not online:
                        detail = f"HTTP {resp.status}"
        except aiohttp.ClientConnectorError:
            detail = "connection refused"
        except asyncio.TimeoutError:
            detail = "timeout"
        except Exception as exc:
            detail = str(exc)

        self._bus.publish(
            OLLAMA_STATUS,
            {"online": online, "detail": detail, "url": self._base_url},
            source=self.name,
        )

    async def _load_model_async(self, model: str) -> None:
        payload = {
            "model": model,
            "prompt": "",
            "stream": False,
            "keep_alive": self._effective_keep_alive(),
        }
        try:
            async with self._open_session() as session:
                async with session.post(
                    f"{self._base_url}/api/generate", json=payload
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(f"load_model failed: {text[:200]}")
            self._loaded_model = model
            self._bus.publish(
                "ollama.model_loaded",
                {"model": model},
                source=self.name,
            )
        except Exception as exc:
            self._publish_error(None, f"Failed to load model: {exc}")

    async def _unload_model_async(self, model: str) -> None:
        payload = {"model": model, "keep_alive": 0}
        try:
            async with self._open_session() as session:
                async with session.post(
                    f"{self._base_url}/api/generate", json=payload
                ) as resp:
                    await resp.read()
            self._loaded_model = None
            self._bus.publish(
                "ollama.model_unloaded",
                {"model": model},
                source=self.name,
            )
        except Exception as exc:
            self._publish_error(None, f"Failed to unload model: {exc}")

    def _open_session(self) -> aiohttp.ClientSession:
        timeout = aiohttp.ClientTimeout(
            total=_REQUEST_TIMEOUT_S,
            connect=_CONNECT_TIMEOUT_S,
        )
        return aiohttp.ClientSession(timeout=timeout)

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
            },
            source=self.name,
        )

        full_text: list[str] = []
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": _LOCAL_ASSISTANT_SYSTEM},
                    {"role": "user", "content": bundle.prompt},
                ],
                "stream": True,
                "options": {"keep_alive": self._effective_keep_alive()},
            }
            async with self._open_session() as session:
                async with session.post(
                    f"{self._base_url}/api/chat", json=payload
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise RuntimeError(
                            f"Ollama returned HTTP {resp.status}: {body[:300]}"
                        )

                    async for raw_line in resp.content:
                        if asyncio.current_task() and asyncio.current_task().cancelled():
                            raise asyncio.CancelledError()
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        chunk = str(data.get("message", {}).get("content", ""))
                        if chunk:
                            full_text.append(chunk)
                            self._bus.publish(
                                CHAT_CHUNK,
                                {
                                    "request_id": request_id,
                                    "text": chunk,
                                },
                                source=self.name,
                            )
                        if data.get("done"):
                            break

            text = "".join(full_text)
            self._bus.publish(
                CHAT_COMPLETE,
                {
                    "request_id": request_id,
                    "text": text,
                    "model": model,
                },
                source=self.name,
            )
        except asyncio.CancelledError:
            self._bus.publish(
                CHAT_CANCELLED,
                {"request_id": request_id},
                source=self.name,
            )
        except aiohttp.ClientConnectorError:
            self._publish_offline(request_id)
        except asyncio.TimeoutError:
            self._publish_error(request_id, "Ollama request timed out.")
        except json.JSONDecodeError as exc:
            self._publish_error(request_id, f"Invalid Ollama response: {exc}")
        except Exception as exc:
            self._publish_error(request_id, str(exc))
        finally:
            self._active_request_id = None
            self._active_future = None

    def _publish_offline(self, request_id: str | None) -> None:
        message = (
            "Ollama is not running. Start Ollama (ollama serve) and try again."
        )
        self._publish_error(request_id, message)
        self._bus.publish(
            OLLAMA_STATUS,
            {"online": False, "detail": "connection refused", "url": self._base_url},
            source=self.name,
        )

    def _publish_error(self, request_id: str | None, message: str) -> None:
        payload: dict[str, Any] = {"message": message}
        if request_id:
            payload["request_id"] = request_id
        self._bus.publish(CHAT_ERROR, payload, source=self.name)
        self._bus.publish(APP_ERROR, {"message": message}, source=self.name)
