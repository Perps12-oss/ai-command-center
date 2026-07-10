"""Brain kernel state machine and recovery coordinator."""

from __future__ import annotations

from collections.abc import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    EXECUTION_RUN_COMPLETE,
    EXECUTION_RUN_FAILED,
    EXECUTION_RUN_STARTED,
    EXECUTION_STEP_APPROVED,
    EXECUTION_STEP_AWAITING_APPROVAL,
    GOAL_ACTIVATED,
    GOAL_PAUSED,
    GOAL_RESUMED,
    KERNEL_RECOVERY_COMPLETED,
    KERNEL_RECOVERY_STARTED,
    KERNEL_STATE_CHANGED,
    KERNEL_TRANSITION_REJECTED,
    PLAN_FAILED,
    PLAN_GENERATED,
)
from ai_command_center.core.world_model.world_model import WorldModel
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.kernel_state import ALLOWED_TRANSITIONS, KernelState
from ai_command_center.services.base import BaseService


class BrainKernelService(BaseService):
    """Formal kernel FSM: BOOT -> RECOVERING/IDLE -> PLANNING/EXECUTING."""

    name = "brain_kernel"

    def __init__(self, bus, world_model: WorldModel) -> None:
        super().__init__(bus)
        self._world_model = world_model
        self._kernel_state = KernelState.BOOT
        self._prior_state: KernelState | None = None
        self._unsubscribers: list[Callable[[], None]] = []

    @property
    def kernel_state(self) -> KernelState:
        return self._kernel_state

    def _on_load(self) -> None:
        self._unsubscribers.extend(
            [
                self._bus.subscribe(GOAL_ACTIVATED, self._on_goal_activated),
                self._bus.subscribe(GOAL_PAUSED, self._on_goal_paused),
                self._bus.subscribe(GOAL_RESUMED, self._on_goal_resumed),
                self._bus.subscribe(PLAN_GENERATED, self._on_plan_generated),
                self._bus.subscribe(PLAN_FAILED, self._on_plan_failed),
                self._bus.subscribe(EXECUTION_RUN_STARTED, self._on_execution_started),
                self._bus.subscribe(
                    EXECUTION_STEP_AWAITING_APPROVAL,
                    self._on_execution_awaiting_approval,
                ),
                self._bus.subscribe(EXECUTION_STEP_APPROVED, self._on_step_approved),
                self._bus.subscribe(EXECUTION_RUN_COMPLETE, self._on_execution_done),
                self._bus.subscribe(EXECUTION_RUN_FAILED, self._on_execution_done),
            ]
        )
        self._recover()

    def _on_unload(self) -> None:
        for unsub in self._unsubscribers:
            unsub()
        self._unsubscribers.clear()
        self._transition(KernelState.SHUTDOWN, CorrelationContext.new())

    def _recover(self) -> None:
        correlation = CorrelationContext.new(action_id="kernel-recovery")
        self._transition(KernelState.RECOVERING, correlation)
        self._bus.publish(
            KERNEL_RECOVERY_STARTED,
            {"correlation": correlation.to_payload()},
            source=self.name,
        )
        mutations = self._world_model.recover(replay_limit=5)
        self._bus.publish(
            KERNEL_RECOVERY_COMPLETED,
            {
                "mutation_count": len(mutations),
                "correlation": correlation.to_payload(),
            },
            source=self.name,
        )
        self._transition(KernelState.IDLE, correlation)

    def _transition(
        self, target: KernelState, correlation: CorrelationContext, *, reason: str = ""
    ) -> bool:
        if target == self._kernel_state:
            return True
        allowed = ALLOWED_TRANSITIONS[self._kernel_state]
        if target not in allowed:
            self._bus.publish(
                KERNEL_TRANSITION_REJECTED,
                {
                    "from": self._kernel_state.value,
                    "to": target.value,
                    "reason": reason or "transition not allowed",
                    "correlation": correlation.to_payload(),
                },
                source=self.name,
            )
            return False
        previous = self._kernel_state
        self._kernel_state = target
        self._bus.publish(
            KERNEL_STATE_CHANGED,
            {
                "from": previous.value,
                "to": target.value,
                "reason": reason,
                "correlation": correlation.to_payload(),
            },
            source=self.name,
        )
        return True

    def _on_goal_activated(self, event: Event) -> None:
        self._transition(
            KernelState.PLANNING,
            CorrelationContext.from_payload(event.payload),
            reason="goal activated",
        )

    def _on_goal_paused(self, event: Event) -> None:
        self._prior_state = self._kernel_state
        self._transition(
            KernelState.PAUSED,
            CorrelationContext.from_payload(event.payload),
            reason="goal paused",
        )

    def _on_goal_resumed(self, event: Event) -> None:
        target = self._prior_state or KernelState.IDLE
        self._prior_state = None
        self._transition(
            target,
            CorrelationContext.from_payload(event.payload),
            reason="goal resumed",
        )

    def _on_plan_generated(self, event: Event) -> None:
        self._transition(
            KernelState.EXECUTING,
            CorrelationContext.from_payload(event.payload),
            reason="plan generated",
        )

    def _on_plan_failed(self, event: Event) -> None:
        self._transition(
            KernelState.IDLE,
            CorrelationContext.from_payload(event.payload),
            reason="plan failed",
        )

    def _on_execution_started(self, event: Event) -> None:
        self._transition(
            KernelState.EXECUTING,
            CorrelationContext.from_payload(event.payload),
            reason="execution started",
        )

    def _on_execution_awaiting_approval(self, event: Event) -> None:
        self._transition(
            KernelState.AWAITING_APPROVAL,
            CorrelationContext.from_payload(event.payload),
            reason="approval required",
        )

    def _on_step_approved(self, event: Event) -> None:
        self._transition(
            KernelState.EXECUTING,
            CorrelationContext.from_payload(event.payload),
            reason="approval granted",
        )

    def _on_execution_done(self, event: Event) -> None:
        self._transition(
            KernelState.IDLE,
            CorrelationContext.from_payload(event.payload),
            reason="execution ended",
        )
