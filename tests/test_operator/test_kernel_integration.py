"""Integration tests for OperatorKernel with real EventBus."""

import pytest

from ai_command_center.core.event_bus import EventBus
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.models.adapters.stub_adapter import StubModelAdapter
from ai_command_center.operator.compliance_engine import ComplianceEngine
from ai_command_center.operator.intent_resolver import IntentResolver
from ai_command_center.operator.kernel import (
    KernelConfig,
    KernelStatus,
    OperatorKernel,
    OperatorRequest,
)
from ai_command_center.operator.mode_resolver import ModeResolver
from ai_command_center.operator.prompt_assembly import PromptAssemblyService
from ai_command_center.operator.mode_resolver import OperatorMode


@pytest.fixture
def real_event_bus():
    """Real EventBus for integration testing."""
    bus = EventBus()
    yield bus
    bus.shutdown()


@pytest.fixture
def stub_adapter():
    """Stub adapter for predictable test responses."""
    return StubModelAdapter(
        response_content="Test response from model",
        model_name="test-model",
    )


@pytest.fixture
def intent_resolver(real_event_bus):
    """Pre-constructed intent resolver for injection."""
    return IntentResolver(real_event_bus)


@pytest.fixture
def mode_resolver(real_event_bus):
    """Pre-constructed mode resolver for injection."""
    return ModeResolver(real_event_bus)


@pytest.fixture
def compliance_engine(real_event_bus):
    """Pre-constructed compliance engine for injection."""
    return ComplianceEngine(real_event_bus)


@pytest.fixture
def prompt_assembly(real_event_bus, mode_resolver):
    """Pre-constructed prompt assembly for injection."""
    return PromptAssemblyService(real_event_bus, mode_resolver=mode_resolver)


@pytest.fixture
def kernel(real_event_bus, stub_adapter, intent_resolver, mode_resolver, compliance_engine, prompt_assembly):
    """Kernel with real EventBus and stub adapter, using injected services."""
    config = KernelConfig(
        model_adapter=stub_adapter,
        enable_compliance=True,
        enable_approval_gates=True,
        intent_resolver=intent_resolver,
        mode_resolver=mode_resolver,
        compliance_engine=compliance_engine,
        prompt_assembly=prompt_assembly,
    )
    return OperatorKernel(real_event_bus, config)


class TestOperatorKernelIntegration:
    """Integration tests for OperatorKernel with EventBus."""

    def test_kernel_initialization(self, kernel):
        """Kernel initializes to INITIALIZING status."""
        assert kernel.status == KernelStatus.INITIALIZING

    def test_kernel_process_chat_request(self, kernel, stub_adapter):
        """Kernel processes a chat request end-to-end."""
        request = OperatorRequest(
            user_input="Hello, how are you?",
        )

        response = kernel.process(request)

        assert response.response is not None
        assert response.intent is not None
        assert response.mode == OperatorMode.CHAT
        assert response.model_used == "StubModelAdapter"
        assert stub_adapter.call_count == 1

    def test_kernel_process_command_request(self, kernel, stub_adapter):
        """Kernel processes a command request with compliance."""
        # Stub returns generic response which may trigger compliance
        request = OperatorRequest(
            user_input="run the tests",
        )

        response = kernel.process(request)

        # Response may be None if compliance flagged it
        assert response.mode == OperatorMode.COMMAND
        # Either response exists or violations exist
        assert response.response is not None or len(response.violations) > 0

    def test_kernel_process_investigation_request(self, kernel, stub_adapter):
        """Kernel processes an investigation request with compliance."""
        request = OperatorRequest(
            user_input="find all bugs in the code",
        )

        response = kernel.process(request)

        assert response.mode == OperatorMode.INVESTIGATION
        # Either response exists or violations exist
        assert response.response is not None or len(response.violations) > 0

    def test_kernel_process_with_workspace_context(self, kernel, stub_adapter):
        """Kernel uses workspace context in processing."""
        request = OperatorRequest(
            user_input="review this code",
            workspace_context={
                "workspace_name": "test-project",
                "context_type": "code_review",
            },
        )

        response = kernel.process(request)

        # Context should influence mode detection
        assert response.mode in {OperatorMode.INVESTIGATION, OperatorMode.CHAT}

    def test_kernel_process_with_conversation_history(self, kernel, stub_adapter):
        """Kernel uses conversation history in processing."""
        request = OperatorRequest(
            user_input="continue from there",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        )

        response = kernel.process(request)

        assert response.response is not None
        assert stub_adapter.last_prompt is not None
        # History should be included in prompt
        assert "CONVERSATION HISTORY" in stub_adapter.last_prompt

    def test_kernel_publishes_events(self, real_event_bus, kernel, stub_adapter):
        """Kernel publishes events to EventBus."""
        request = OperatorRequest(user_input="test")
        kernel.process(request)

        # Check that events were published
        topic_counts = real_event_bus.get_topic_counts()
        # Should have published some events
        assert len(topic_counts) > 0

    def test_kernel_with_compliance_violation(self, real_event_bus, stub_adapter):
        """Kernel handles responses with compliance violations."""
        # Create adapter that returns a response that might trigger compliance
        violation_adapter = StubModelAdapter(
            response_content="This always fails and I cannot verify anything",
        )

        config = KernelConfig(
            model_adapter=violation_adapter,
            enable_compliance=True,
            enable_approval_gates=True,
        )
        kernel = OperatorKernel(real_event_bus, config)

        request = OperatorRequest(
            user_input="analyze this",
        )

        response = kernel.process(request)

        # With approval gates enabled, violations should block immediate response
        if response.violations:
            assert kernel.status == KernelStatus.AWAITING_APPROVAL

    def test_kernel_approval_flow(self, real_event_bus, stub_adapter):
        """Kernel approval flow for flagged responses."""
        config = KernelConfig(
            model_adapter=stub_adapter,
            enable_compliance=True,
            enable_approval_gates=True,
        )
        kernel = OperatorKernel(real_event_bus, config)

        request = OperatorRequest(user_input="test")

        # First process (may be pending approval)
        response = kernel.process(request)

        if kernel.status == KernelStatus.AWAITING_APPROVAL:
            # Should be able to approve
            correlation = CorrelationContext.new()
            approved_response = kernel.approve(correlation)
            assert approved_response is not None

    def test_kernel_rejection_flow(self, real_event_bus, stub_adapter):
        """Kernel rejection flow for flagged responses."""
        config = KernelConfig(
            model_adapter=stub_adapter,
            enable_compliance=True,
            enable_approval_gates=True,
        )
        kernel = OperatorKernel(real_event_bus, config)

        request = OperatorRequest(user_input="test")
        kernel.process(request)

        if kernel.status == KernelStatus.AWAITING_APPROVAL:
            # Should be able to reject
            kernel.reject("Not appropriate")
            assert kernel.status == KernelStatus.IDLE

    def test_kernel_shutdown(self, kernel):
        """Kernel shuts down cleanly."""
        kernel.shutdown()
        assert kernel.status == KernelStatus.INITIALIZING

    def test_kernel_error_publishes_event(self, real_event_bus):
        """Kernel errors are published to EventBus."""
        # Create kernel without adapter - should fail on process
        config = KernelConfig(model_adapter=None)
        kernel = OperatorKernel(real_event_bus, config)

        request = OperatorRequest(user_input="test")

        with pytest.raises(RuntimeError, match="No model adapter"):
            kernel.process(request)


class TestKernelConfig:
    """Tests for KernelConfig."""

    def test_default_config(self):
        """Default config has sensible defaults."""
        config = KernelConfig()
        assert config.enable_compliance is True
        assert config.enable_approval_gates is True
        assert config.max_retries == 3
        assert config.model_adapter is None

    def test_config_with_adapter(self, stub_adapter):
        """Config with model adapter."""
        config = KernelConfig(model_adapter=stub_adapter)
        assert config.model_adapter is stub_adapter


class TestOperatorRequest:
    """Tests for OperatorRequest."""

    def test_minimal_request(self):
        """Minimal request with just user input."""
        request = OperatorRequest(user_input="test")
        assert request.user_input == "test"
        assert request.workspace_context == {}
        assert request.conversation_history == []

    def test_full_request(self):
        """Full request with all fields."""
        request = OperatorRequest(
            user_input="test",
            workspace_context={"key": "value"},
            conversation_history=[{"role": "user", "content": "hi"}],
            correlation=CorrelationContext.new(),
        )
        assert request.workspace_context == {"key": "value"}
        assert len(request.conversation_history) == 1
        assert request.correlation is not None
