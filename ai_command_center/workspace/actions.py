"""Action Architecture (Reference Architecture v3.5, Part VI).

The system operates on **actions**, not raw text. Resolution and execution produce
structured :class:`ActionResult` values; an :class:`OutputTarget` knows how to deliver
a result. This layer is pure: targets declare what they accept and how to dispatch,
but the real OS side effects (SendInput, shell, Obsidian, browser, VS Code) are
supplied by injected adapters in higher layers — nothing here performs I/O.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path


class ActionResult:
    """Base type for all structured action outcomes."""


@dataclass(frozen=True, slots=True)
class TextInsertion(ActionResult):
    text: str


@dataclass(frozen=True, slots=True)
class OpenFile(ActionResult):
    path: Path


@dataclass(frozen=True, slots=True)
class LaunchApplication(ActionResult):
    executable: str


@dataclass(frozen=True, slots=True)
class RunCommand(ActionResult):
    command: str


@dataclass(frozen=True, slots=True)
class CreateNote(ActionResult):
    title: str
    content: str


class OutputTarget:
    """Destination that can deliver an :class:`ActionResult`.

    ``accepts`` lets a dispatcher route a result to the first capable target;
    ``dispatch`` returns ``True`` on successful delivery. Subclasses (or injected
    adapters) implement the side effects.
    """

    def accepts(self, result: ActionResult) -> bool:
        return True

    def dispatch(self, result: ActionResult) -> bool:  # pragma: no cover - interface
        raise NotImplementedError


class CallableTarget(OutputTarget):
    """Adapter turning a handler callable into a target for given action types.

    Keeps OS-specific delivery code out of this layer: the handler is injected and
    returns ``True`` on success. ``action_types`` restricts what the target accepts.
    """

    def __init__(
        self,
        action_types: type[ActionResult] | tuple[type[ActionResult], ...],
        handler: Callable[[ActionResult], bool],
        *,
        name: str | None = None,
    ) -> None:
        self._action_types = (
            action_types if isinstance(action_types, tuple) else (action_types,)
        )
        self._handler = handler
        self.name = name or "CallableTarget"

    def accepts(self, result: ActionResult) -> bool:
        return isinstance(result, self._action_types)

    def dispatch(self, result: ActionResult) -> bool:
        if not self.accepts(result):
            return False
        return bool(self._handler(result))


@dataclass(frozen=True, slots=True)
class DispatchOutcome:
    """Result of routing one action to a target (Part V Phase 4 — Delivery)."""

    accepted: bool
    success: bool
    target: str | None = None
    error: str | None = None


class ActionDispatcher:
    """Routes an :class:`ActionResult` to the first registered target that accepts it.

    Deterministic: targets are tried in registration order. A target raising during
    dispatch is isolated — the outcome records the failure rather than propagating.
    """

    def __init__(self, targets: Iterable[OutputTarget] = ()) -> None:
        self._targets: list[OutputTarget] = list(targets)

    def register(self, target: OutputTarget) -> None:
        self._targets.append(target)

    def dispatch(self, result: ActionResult) -> DispatchOutcome:
        for target in self._targets:
            if not target.accepts(result):
                continue
            name = getattr(target, "name", type(target).__name__)
            try:
                success = bool(target.dispatch(result))
            except Exception as exc:  # noqa: BLE001 - isolate target failures
                return DispatchOutcome(
                    accepted=True,
                    success=False,
                    target=name,
                    error=f"{type(exc).__name__}: {exc}",
                )
            return DispatchOutcome(accepted=True, success=success, target=name)
        return DispatchOutcome(accepted=False, success=False)
