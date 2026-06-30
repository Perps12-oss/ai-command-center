"""Thread-based timeout helper.

The production ``ServiceManager`` does not (yet) enforce per-call timeouts on
service ``start``/``stop``. These helpers provide a watchdog wrapper used by the
lifecycle deadlock tests to prove that a hanging ``unload`` can be detected and
surfaced as a timeout *without freezing the calling (UI) thread*.

The wrapper is deliberately conservative: the worker thread is a daemon, so a
genuinely deadlocked call cannot block interpreter shutdown.
"""

from __future__ import annotations

import builtins
import threading
from typing import Any, Callable

_BuiltinTimeoutError = builtins.TimeoutError


# Subclass the builtin so callers may assert against either name.
class TimeoutError(_BuiltinTimeoutError):  # noqa: A001 - intentional shadow
    """Raised when a wrapped call exceeds its allotted wall-clock budget."""


def run_with_timeout(
    func: Callable[..., Any],
    *args: Any,
    timeout: float,
    name: str = "watchdog-call",
    **kwargs: Any,
) -> Any:
    """Run ``func(*args, **kwargs)`` but give up after ``timeout`` seconds.

    Returns the function result on success. Re-raises any exception raised by
    ``func``. Raises :class:`TimeoutError` (a subclass of the builtin
    ``TimeoutError``) if the call does not complete in time. The worker runs as
    a daemon thread so a hung call never blocks the test process.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = func(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - propagate to caller thread
            error["exc"] = exc

    worker = threading.Thread(target=_runner, name=name, daemon=True)
    worker.start()
    worker.join(timeout)

    if worker.is_alive():
        raise TimeoutError(
            f"call {getattr(func, '__name__', func)!r} did not complete within "
            f"{timeout:.2f}s (still running — likely deadlocked)"
        )
    if "exc" in error:
        raise error["exc"]
    return result.get("value")
