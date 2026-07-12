"""OperatorKernel — core orchestration for model-agnostic operator behavior.

The kernel owns:
- Behavior rules and governance
- Intent and mode resolution
- Prompt assembly
- Compliance validation
- Response rendering

The model owns:
- Reasoning
- Summarization
- Planning assistance

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from ai_command_center.domain.correlation import CorrelationContext

if TYPE_CHECKING:
    from ai_command_center.core.event_bus import EventBus
    from ai_command_center.models.base import ModelAdapter
    from ai_command_center.operator.intent_resolver import IntentType
    from ai_command_center.operator.mode_resolver import OperatorMode
    from ai_command_center.operator.compliance_engine import ComplianceViolation
    from ai_command_center.operator.prompt_assembly import PromptAssemblyService


class KernelStatus(str, Enum):
    """OperatorKernel lifecycle states."""

    INITIALIZING = "initializing"
    IDLE = "idle"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLIANCE_CHECK = "compliance_check"
    ERROR = "error"


@dataclass
class OperatorRequest:
    """Input to the OperatorKernel."""

    user_input: str
    workspace_context: dict[str, Any] = field(default_factory=dict)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    correlation: CorrelationContext | None = None


@dataclass
class OperatorResponse:
    """Output from the OperatorKernel."""

    response: Any  # Typed response conforming to ResponseContract
    intent: IntentType | None = None
    mode: OperatorMode | None = None
    violations: list[ComplianceViolation] = field(default_factory=list)
    model_used: str | None = None
    correlation: CorrelationContext | None = None


@dataclass
class KernelConfig:
    """Configuration for the OperatorKernel."""

    model_adapter: ModelAdapter | None = None
    enable_compliance: bool = True
    enable_approval_gates: bool = True
    max_retries: int = 3
    # Pre-constructed services (for composition root injection)
    intent_resolver: Any = None
    mode_resolver: Any = None
    compliance_engine: Any = None
    prompt_assembly: PromptAssemblyService | None = None


class OperatorKernel:
    """Single source of operational behavior for model-agnostic operator."""

    def __init__(
        self,
        bus: EventBus,
        config: KernelConfig | None = None,
    ) -> None:
        self._bus = bus
        self._config = config or KernelConfig()

        # Sub-components (use injected or create in _initialize)
        self._intent_resolver: Any = None
        self._mode_resolver: Any = None
        self._prompt_assembly: PromptAssemblyService | None = None
        self._compliance_engine: Any = None

        # State
        self._status = KernelStatus.INITIALIZING
        self._current_request: OperatorRequest | None = None

    @property
    def status(self) -> KernelStatus:
        """Return current kernel status."""
        return self._status

    def _initialize(self) -> None:
        """Initialize sub-components. Called on first request if not injected."""
        # Use injected services if available
        if self._config.intent_resolver is not None:
            self._intent_resolver = self._config.intent_resolver
        else:
            from ai_command_center.operator.intent_resolver import IntentResolver
            self._intent_resolver = IntentResolver(self._bus)

        if self._config.mode_resolver is not None:
            self._mode_resolver = self._config.mode_resolver
        else:
            from ai_command_center.operator.mode_resolver import ModeResolver
            self._mode_resolver = ModeResolver(self._bus)

        if self._config.compliance_engine is not None:
            self._compliance_engine = self._config.compliance_engine
        else:
            from ai_command_center.operator.compliance_engine import ComplianceEngine
            self._compliance_engine = ComplianceEngine(self._bus)

        if self._config.prompt_assembly is not None:
            self._prompt_assembly = self._config.prompt_assembly
        else:
            from ai_command_center.operator.prompt_assembly import PromptAssemblyService
            self._prompt_assembly = PromptAssemblyService(
                self._bus,
                mode_resolver=self._mode_resolver,
            )

    def process(self, request: OperatorRequest) -> OperatorResponse:
        """Process a user request through the operator pipeline.

        Pipeline:
        1. Intent resolution
        2. Mode detection
        3. Prompt assembly
        4. Model inference
        5. Compliance validation
        6. Response rendering
        """
        if self._status == KernelStatus.INITIALIZING:
            self._initialize()

        correlation = request.correlation or CorrelationContext.new(action_id="operator")
        self._current_request = request
        self._status = KernelStatus.PROCESSING

        try:
            # Step 1: Classify intent
            intent = self._intent_resolver.resolve(
                request.user_input,
                request.conversation_history,
            )

            # Step 2: Detect operator mode
            mode = self._mode_resolver.resolve(
                intent,
                request.user_input,
                request.workspace_context,
            )

            # Step 3: Assemble prompt
            assert self._prompt_assembly is not None
            prompt = self._prompt_assembly.assemble(
                mode=mode,
                intent=intent,
                user_input=request.user_input,
                workspace_context=request.workspace_context,
                conversation_history=request.conversation_history,
            )

            # Step 4: Model inference
            model_response = self._invoke_model(prompt, mode)

            # Step 5: Compliance validation
            violations: list[Any] = []
            if self._config.enable_compliance:
                assert self._compliance_engine is not None
                violations = self._compliance_engine.validate(
                    response=model_response,
                    mode=mode,
                    workspace_context=request.workspace_context,
                )

                if violations and self._config.enable_approval_gates:
                    self._status = KernelStatus.AWAITING_APPROVAL
                    # Return pending response for approval flow
                    return OperatorResponse(
                        response=None,
                        intent=intent.intent_type,
                        mode=mode,
                        violations=violations,
                        correlation=correlation,
                    )

            # Step 6: Build typed response
            response = self._build_response(model_response, mode)

            self._status = KernelStatus.IDLE
            return OperatorResponse(
                response=response,
                intent=intent.intent_type,
                mode=mode,
                violations=violations,
                model_used=self._config.model_adapter.__class__.__name__
                    if self._config.model_adapter
                    else None,
                correlation=correlation,
            )

        except Exception as exc:
            self._status = KernelStatus.ERROR
            self._bus.publish(
                "kernel.error",
                {
                    "error": str(exc),
                    "correlation": correlation.to_payload()
                    if correlation
                    else None,
                },
                source="operator_kernel",
            )
            raise

    def _invoke_model(self, prompt: str, mode: Any) -> str:
        """Invoke the configured model adapter."""
        if self._config.model_adapter is None:
            raise RuntimeError("No model adapter configured")

        response = self._config.model_adapter.complete(prompt)
        return response.content

    def _build_response(self, content: str, mode: Any) -> Any:
        """Build a typed response conforming to the mode's contract."""
        from ai_command_center.operator.response_contracts import (
            ChatResponse,
            CommandResponse,
            InvestigationResponse,
            ArchitectResponse,
        )

        if mode.value == "chat":
            return ChatResponse(message=content)
        elif mode.value == "command":
            return CommandResponse(command=content)
        elif mode.value == "investigation":
            return InvestigationResponse(findings=[content])
        elif mode.value == "architect":
            return ArchitectResponse(design=content)
        else:
            return ChatResponse(message=content)

    def approve(self, correlation: CorrelationContext) -> OperatorResponse:
        """Proceed with a previously flagged response after user approval."""
        if self._status != KernelStatus.AWAITING_APPROVAL:
            raise RuntimeError("No pending approval")

        if self._current_request is None:
            raise RuntimeError("No current request")

        # Re-validate and proceed
        self._status = KernelStatus.PROCESSING
        return self.process(self._current_request)

    def reject(self, reason: str) -> None:
        """Reject a previously flagged response."""
        if self._status != KernelStatus.AWAITING_APPROVAL:
            raise RuntimeError("No pending approval")

        self._bus.publish(
            "kernel.response.rejected",
            {"reason": reason},
            source="operator_kernel",
        )
        self._status = KernelStatus.IDLE
        self._current_request = None

    def shutdown(self) -> None:
        """Shutdown the kernel and release resources."""
        self._status = KernelStatus.INITIALIZING
        self._current_request = None


__all__ = [
    "KernelConfig",
    "KernelStatus",
    "OperatorKernel",
    "OperatorRequest",
    "OperatorResponse",
]
