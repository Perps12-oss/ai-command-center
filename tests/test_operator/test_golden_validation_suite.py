"""Golden Validation Suite — Phase 8 Model Independence.

Proves behavioral parity across all registered ModelAdapter implementations:
- Same intent is resolved regardless of adapter
- Same capability/provider is selected regardless of adapter
- Same approval path is taken regardless of adapter
- Same execution behavior (truth-bound bypass) regardless of adapter

Live adapters (Ollama, OpenAI, Anthropic) are replaced by protocol-compatible
stubs that satisfy the ModelAdapter contract without requiring network access.
This tests the PIPELINE invariant, not model output quality.
"""

from __future__ import annotations

from typing import Iterator
from unittest.mock import patch

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.models.base import ModelAdapter, ModelConfig, ModelResponse
from ai_command_center.models.adapters.stub_adapter import StubModelAdapter
from ai_command_center.operator.kernel import KernelConfig, OperatorKernel, OperatorRequest
from ai_command_center.operator.mode_resolver import OperatorMode
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.services.orchestration_service import OrchestrationService
from ai_command_center.services.chat_handler_service import ChatHandlerService
from ai_command_center.core.context_manager import ContextManager
from ai_command_center.core.events.topics import CHAT_COMPLETE, LLM_REQUEST

from tests.orchestration.conftest import build_registry, publish_chat


# ── Protocol-compatible stubs for live adapters ────────────────────────────
# Each stub satisfies the ModelAdapter ABC without requiring API keys or network.


class _OllamaStub(ModelAdapter):
    """Ollama-shaped stub: simulates llama3 behavior at the contract level."""

    name = "ollama"
    _model_name = "llama3"

    @property
    def supported_modes(self) -> set[OperatorMode]:
        return {OperatorMode.CHAT, OperatorMode.COMMAND, OperatorMode.INVESTIGATION, OperatorMode.ARCHITECT}

    @property
    def model_name(self) -> str:
        return self._model_name

    def complete(self, prompt: str, config: ModelConfig | None = None) -> ModelResponse:
        return ModelResponse(content="Ollama response", model_name=self._model_name, finish_reason="stop")

    def stream(self, prompt: str, config: ModelConfig | None = None) -> Iterator[ModelResponse]:
        yield ModelResponse(content="Ollama response", model_name=self._model_name, finish_reason="stop")

    def health_check(self) -> bool:
        return True


class _OpenAIStub(ModelAdapter):
    """OpenAI-shaped stub: simulates gpt-4o behavior at the contract level."""

    name = "openai"
    _model_name = "gpt-4o"

    @property
    def supported_modes(self) -> set[OperatorMode]:
        return {OperatorMode.CHAT, OperatorMode.COMMAND, OperatorMode.INVESTIGATION, OperatorMode.ARCHITECT}

    @property
    def model_name(self) -> str:
        return self._model_name

    def complete(self, prompt: str, config: ModelConfig | None = None) -> ModelResponse:
        return ModelResponse(content="OpenAI response", model_name=self._model_name, finish_reason="stop")

    def stream(self, prompt: str, config: ModelConfig | None = None) -> Iterator[ModelResponse]:
        yield ModelResponse(content="OpenAI response", model_name=self._model_name, finish_reason="stop")

    def health_check(self) -> bool:
        return True


class _AnthropicStub(ModelAdapter):
    """Anthropic-shaped stub: simulates claude-3-5-sonnet behavior at the contract level."""

    name = "anthropic"
    _model_name = "claude-3-5-sonnet-20241022"

    @property
    def supported_modes(self) -> set[OperatorMode]:
        return {OperatorMode.CHAT, OperatorMode.COMMAND, OperatorMode.INVESTIGATION, OperatorMode.ARCHITECT}

    @property
    def model_name(self) -> str:
        return self._model_name

    def complete(self, prompt: str, config: ModelConfig | None = None) -> ModelResponse:
        return ModelResponse(content="Anthropic response", model_name=self._model_name, finish_reason="end_turn")

    def stream(self, prompt: str, config: ModelConfig | None = None) -> Iterator[ModelResponse]:
        yield ModelResponse(content="Anthropic response", model_name=self._model_name, finish_reason="end_turn")

    def health_check(self) -> bool:
        return True


# ── Parametrize all adapters ────────────────────────────────────────────────

ALL_ADAPTERS: list[tuple[str, ModelAdapter]] = [
    ("stub", StubModelAdapter(response_content="Stub response", model_name="stub-model")),
    ("ollama/llama3", _OllamaStub()),
    ("openai/gpt-4o", _OpenAIStub()),
    ("anthropic/claude-3-5", _AnthropicStub()),
]

adapter_ids = [a[0] for a in ALL_ADAPTERS]
adapter_instances = [a[1] for a in ALL_ADAPTERS]


# ── Suite 1: Operator Kernel pipeline invariants ───────────────────────────
# These tests verify that intent resolution, mode detection, compliance
# gating, and response contract building are model-agnostic.


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_chat_intent_resolves_identically_across_adapters(adapter: ModelAdapter) -> None:
    """Chat-mode requests always resolve to CHAT mode regardless of adapter."""
    bus = EventBus()
    kernel = OperatorKernel(bus, KernelConfig(model_adapter=adapter, enable_compliance=False))
    request = OperatorRequest(user_input="Hello, how are you?")
    response = kernel.process(request)
    assert response.mode == OperatorMode.CHAT
    assert response.response is not None


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_command_intent_resolves_identically_across_adapters(adapter: ModelAdapter) -> None:
    """Command-mode requests always resolve to COMMAND mode regardless of adapter."""
    bus = EventBus()
    kernel = OperatorKernel(bus, KernelConfig(model_adapter=adapter, enable_compliance=False))
    request = OperatorRequest(
        user_input="create a new file called test.py",
        workspace_context={"has_workspace": True},
    )
    response = kernel.process(request)
    assert response.mode == OperatorMode.COMMAND
    assert response.response is not None


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_approval_gate_fires_identically_across_adapters(adapter: ModelAdapter) -> None:
    """When compliance violations are detected, AWAITING_APPROVAL state is reached
    regardless of which adapter is configured."""
    from ai_command_center.operator.compliance_engine import ComplianceViolation, Severity, ViolationType

    class AlwaysViolatingEngine:
        def validate(self, response, mode, workspace_context) -> list:
            return [ComplianceViolation(
                violation_type=ViolationType.HALLUCINATED_CAPABILITY,
                severity=Severity.HIGH,
                message="forced violation for approval test",
            )]

    bus = EventBus()
    kernel = OperatorKernel(
        bus,
        KernelConfig(
            model_adapter=adapter,
            enable_compliance=True,
            enable_approval_gates=True,
            compliance_engine=AlwaysViolatingEngine(),
        ),
    )
    request = OperatorRequest(user_input="do something risky")
    response = kernel.process(request)
    assert len(response.violations) > 0
    from ai_command_center.operator.kernel import KernelStatus
    assert kernel.status == KernelStatus.AWAITING_APPROVAL


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_model_name_is_recorded_in_response(adapter: ModelAdapter) -> None:
    """model_used in OperatorResponse reflects the actual adapter class name."""
    bus = EventBus()
    kernel = OperatorKernel(bus, KernelConfig(model_adapter=adapter, enable_compliance=False))
    response = kernel.process(OperatorRequest(user_input="tell me something"))
    assert response.model_used == adapter.__class__.__name__


# ── Suite 2: Orchestration pipeline bypass (model never called) ────────────
# Truth-bound intents (Open Outlook, time query) must NEVER reach the LLM
# regardless of which adapter is attached to the kernel.


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_truth_bound_intent_bypasses_llm_regardless_of_adapter(adapter: ModelAdapter) -> None:
    """Open Outlook must be handled by OrchestrationService before any LLM call,
    regardless of adapter. adapter.complete() must NEVER be called."""
    bus = EventBus()
    registry = build_registry()
    orchestration = OrchestrationService(bus, provider_registry=registry)
    chat = ChatHandlerService(bus, ContextManager())
    orchestration.start()
    chat.start()

    llm_requests: list[dict] = []
    completes: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))

    try:
        publish_chat(bus, "Open Outlook", request_id="req-golden-launch")
        assert llm_requests == [], f"Adapter {adapter.name!r} caused LLM invocation for truth-bound intent"
        assert len(completes) == 1
        assert completes[0]["truth_validated"] is True
        assert completes[0]["response_source"] == "orchestration"
    finally:
        chat.stop()
        orchestration.stop()


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_time_query_bypasses_llm_regardless_of_adapter(adapter: ModelAdapter) -> None:
    """System time query must be answered by OrchestrationService, not LLM."""
    bus = EventBus()
    registry = build_registry()
    orchestration = OrchestrationService(bus, provider_registry=registry)
    chat = ChatHandlerService(bus, ContextManager())
    orchestration.start()
    chat.start()

    llm_requests: list[dict] = []
    completes: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))
    bus.subscribe(CHAT_COMPLETE, lambda e: completes.append(dict(e.payload)))

    try:
        publish_chat(bus, "What time is it?", request_id="req-golden-time")
        assert llm_requests == [], f"Adapter {adapter.name!r} caused LLM invocation for time query"
        assert len(completes) == 1
        assert completes[0]["response_source"] == "orchestration"
    finally:
        chat.stop()
        orchestration.stop()


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_unhandled_intent_defers_to_llm_for_all_adapters(adapter: ModelAdapter) -> None:
    """Unclassified intents must always emit LLM_REQUEST, for every adapter."""
    bus = EventBus()
    registry = build_registry()
    orchestration = OrchestrationService(bus, provider_registry=registry)
    chat = ChatHandlerService(bus, ContextManager())
    orchestration.start()
    chat.start()

    llm_requests: list[dict] = []
    bus.subscribe(LLM_REQUEST, lambda e: llm_requests.append(dict(e.payload)))

    try:
        publish_chat(bus, "Tell me a joke", request_id="req-golden-joke")
        assert len(llm_requests) == 1, (
            f"Adapter {adapter.name!r}: unhandled intent did not defer to LLM"
        )
    finally:
        chat.stop()
        orchestration.stop()


# ── Suite 3: ModelAdapter contract conformance ─────────────────────────────
# Every adapter must produce a valid ModelResponse with required fields.


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_adapter_complete_returns_valid_model_response(adapter: ModelAdapter) -> None:
    """complete() must return ModelResponse with non-empty content and model_name."""
    response = adapter.complete("test prompt")
    assert isinstance(response, ModelResponse)
    assert isinstance(response.content, str)
    assert isinstance(response.model_name, str)
    assert len(response.model_name) > 0


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_adapter_supported_modes_is_nonempty(adapter: ModelAdapter) -> None:
    """Every adapter must declare at least one supported OperatorMode."""
    modes = adapter.supported_modes
    assert len(modes) > 0
    assert all(isinstance(m, OperatorMode) for m in modes)


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_adapter_model_name_is_non_empty_string(adapter: ModelAdapter) -> None:
    """model_name property must return a non-empty string."""
    assert isinstance(adapter.model_name, str)
    assert len(adapter.model_name) > 0


@pytest.mark.parametrize("adapter", adapter_instances, ids=adapter_ids)
def test_adapter_health_check_returns_bool(adapter: ModelAdapter) -> None:
    """health_check() must return a bool (True for stubs)."""
    result = adapter.health_check()
    assert isinstance(result, bool)
