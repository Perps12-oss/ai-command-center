"""Risk area #1 - emulation-aware end-to-end smoke test.

Two deliverables:

1. A *headless* end-to-end smoke of the event-driven core (EventBus -> AppState
   -> Stub Ollama chat) that runs on any platform. It proves a "send a chat
   message" flow completes without spawning a crashing x64 subprocess.

2. A Windows test that attempts to disable x64 emulation for the process via
   ``SetProcessMachineTypeToEmulate`` and - whether or not that succeeds -
   asserts that every child process shares the parent's architecture (i.e. no
   hidden x64 subprocess was spawned). Uses ``win32process``/``psutil``.
"""

from __future__ import annotations

import sys

import pytest


def _run_headless_chat_smoke() -> list[str]:
    """Drive a full chat round-trip through the real core; return chunk texts."""
    from ai_command_center.core.app_state import AppStateStore
    from ai_command_center.core.context_manager import ContextBundle
    from ai_command_center.core.events.topics import CHAT_CHUNK, CHAT_COMPLETE
    from ai_command_center.services.ollama_service import StubOllamaService
    from tests.support import RecordingEventBus

    bus = RecordingEventBus()
    store = AppStateStore(bus)
    ollama = StubOllamaService(bus)
    ollama.start()

    chunks: list[str] = []
    bus.subscribe(CHAT_CHUNK, lambda e: chunks.append(e.payload["text"]))

    bundle = ContextBundle(prompt="hello world", sources=("smoke",), token_estimate=3)
    try:
        ollama.stream_chat(bundle, model="fake-model")
    finally:
        ollama.stop()
        store.close()

    completed = bus.events_for(CHAT_COMPLETE)
    assert completed, "chat.complete was never published - smoke flow broke"
    assert store.snapshot.chat_status == "complete", (
        f"AppState should be 'complete', got {store.snapshot.chat_status!r}"
    )
    return chunks


def test_headless_chat_smoke_completes() -> None:
    chunks = _run_headless_chat_smoke()
    assert "".join(chunks), "expected streamed chat output, got nothing"


def _try_disable_x64_emulation() -> tuple[bool, str]:
    """Best-effort: disable x64 emulation for this process (Win11 ARM64 API)."""
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        fn = getattr(kernel32, "SetProcessMachineTypeToEmulate", None)
        if fn is None:
            return False, "SetProcessMachineTypeToEmulate not available"
        IMAGE_FILE_MACHINE_UNKNOWN = 0x0  # 0 disables emulation
        fn.restype = ctypes.c_long  # HRESULT
        hr = fn(ctypes.c_ushort(IMAGE_FILE_MACHINE_UNKNOWN))
        return (hr == 0), f"HRESULT=0x{hr & 0xFFFFFFFF:08X}"
    except (OSError, AttributeError, ValueError) as exc:
        return False, str(exc)


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only emulation gate")
def test_no_x64_subprocesses_during_smoke() -> None:
    """After the smoke flow, no child process may differ in architecture."""
    import psutil

    disabled, detail = _try_disable_x64_emulation()
    # We do not require the call to succeed (it only exists on Win11 ARM64), but
    # we record the outcome for diagnostics.
    print(f"x64 emulation disable attempt: success={disabled} ({detail})")

    _run_headless_chat_smoke()

    parent = psutil.Process()
    children = parent.children(recursive=True)
    # The headless flow must not fork native helper processes at all.
    alive = [c for c in children if c.is_running()]
    assert not alive, (
        "headless chat smoke unexpectedly spawned subprocess(es): "
        + ", ".join(f"{c.pid}:{c.name()}" for c in alive)
    )
