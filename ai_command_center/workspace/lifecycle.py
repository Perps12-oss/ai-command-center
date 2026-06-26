"""Runtime Lifecycle (Reference Architecture v3.5, Part V).

A deterministic state machine that sequences a single invocation through its phases
and wires together the prior domain layers:

    0A Invocation          -> palette created (no blocking ops modeled here)
    0B Context Acquisition -> ContextAcquirer.acquire()           (Part III)
    1  Hydration           -> SuggestionEngine.suggest()          (Part VII)
    2  Intent Resolution   -> IntentResolver.resolve()            (Part IV)
    3  Execution           -> ActionDispatcher.dispatch()         (Part VI)
    4  Delivery            -> dispatch outcome carried to target

The pipeline is pure: collaborators are injected and the result is a structured,
inspectable trace. Per Part IV, only an ``AUTO_EXECUTE`` resolution carrying an
``ActionResult`` reaches execution — ambiguous (suggest/clarify) intents never
silently execute.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ai_command_center.workspace.actions import (
    ActionDispatcher,
    ActionResult,
    DispatchOutcome,
)
from ai_command_center.workspace.context_acquisition import (
    AcquiredContext,
    ContextAcquirer,
)
from ai_command_center.workspace.intent import (
    IntentResolution,
    IntentResolver,
    ResolutionCandidate,
)
from ai_command_center.workspace.suggestions import Suggestion, SuggestionEngine


class LifecyclePhase(IntEnum):
    """Ordered runtime phases for a single invocation."""

    INVOCATION = 0
    CONTEXT_ACQUISITION = 1
    HYDRATION = 2
    INTENT_RESOLUTION = 3
    EXECUTION = 4
    DELIVERY = 5

    @property
    def label(self) -> str:
        return {
            LifecyclePhase.INVOCATION: "0A",
            LifecyclePhase.CONTEXT_ACQUISITION: "0B",
            LifecyclePhase.HYDRATION: "1",
            LifecyclePhase.INTENT_RESOLUTION: "2",
            LifecyclePhase.EXECUTION: "3",
            LifecyclePhase.DELIVERY: "4",
        }[self]


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    """Structured trace of one invocation through the runtime lifecycle."""

    phases: tuple[LifecyclePhase, ...]
    context: AcquiredContext
    suggestions: tuple[Suggestion, ...]
    resolution: IntentResolution
    executed: bool
    delivery: DispatchOutcome | None = None

    @property
    def reached(self) -> LifecyclePhase:
        return self.phases[-1]


class RuntimePipeline:
    """Deterministically drives an invocation through the lifecycle phases."""

    def __init__(
        self,
        acquirer: ContextAcquirer,
        suggestion_engine: SuggestionEngine,
        resolver: IntentResolver,
        dispatcher: ActionDispatcher,
    ) -> None:
        self._acquirer = acquirer
        self._suggestions = suggestion_engine
        self._resolver = resolver
        self._dispatcher = dispatcher

    def run(
        self,
        candidates: tuple[ResolutionCandidate, ...] = (),
        *,
        include_ui_automation: bool = False,
    ) -> LifecycleResult:
        phases: list[LifecyclePhase] = [LifecyclePhase.INVOCATION]

        # 0B — Context Acquisition
        context = self._acquirer.acquire(include_ui_automation=include_ui_automation)
        phases.append(LifecyclePhase.CONTEXT_ACQUISITION)

        # 1 — Hydration (suggestions before AI reasoning)
        suggestions = self._suggestions.suggest(context)
        phases.append(LifecyclePhase.HYDRATION)

        # 2 — Intent Resolution (deterministic; exposes confidence)
        resolution = self._resolver.resolve(candidates)
        phases.append(LifecyclePhase.INTENT_RESOLUTION)

        # 3/4 — Execution + Delivery, only when unambiguous and action-bearing
        executed = False
        delivery: DispatchOutcome | None = None
        if (
            resolution.should_auto_execute
            and resolution.best is not None
            and isinstance(resolution.best.target, ActionResult)
        ):
            phases.append(LifecyclePhase.EXECUTION)
            delivery = self._dispatcher.dispatch(resolution.best.target)
            executed = True
            phases.append(LifecyclePhase.DELIVERY)

        return LifecycleResult(
            phases=tuple(phases),
            context=context,
            suggestions=suggestions,
            resolution=resolution,
            executed=executed,
            delivery=delivery,
        )
