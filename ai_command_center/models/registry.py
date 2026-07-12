"""ModelRegistry — registry for model adapters.

Reference: docs/plans/PHASE_8_OPERATOR_KERNEL_PLAN.md Section 8.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_command_center.models.base import ModelAdapter, ModelConfig, ModelResponse

if TYPE_CHECKING:
    from ai_command_center.operator.mode_resolver import OperatorMode


class ModelRegistry:
    """Registry for model adapters.

    Allows runtime selection of model provider based on:
    - Availability
    - Capability requirements
    - Configuration
    """

    def __init__(self) -> None:
        self._adapters: dict[str, ModelAdapter] = {}
        self._default: str | None = None

    def register(
        self,
        name: str,
        adapter: ModelAdapter,
        set_default: bool = False,
    ) -> None:
        """Register a model adapter.

        Args:
            name: Identifier for this adapter
            adapter: The ModelAdapter instance
            set_default: If True, set this as the default adapter
        """
        self._adapters[name] = adapter
        if set_default or self._default is None:
            self._default = name

    def get(self, name: str) -> ModelAdapter | None:
        """Get an adapter by name."""
        return self._adapters.get(name)

    def get_default(self) -> ModelAdapter | None:
        """Get the default adapter."""
        if self._default is None:
            return None
        return self._adapters.get(self._default)

    def set_default(self, name: str) -> bool:
        """Set the default adapter by name.

        Returns True if successful, False if adapter not found.
        """
        if name not in self._adapters:
            return False
        self._default = name
        return True

    def list_adapters(self) -> list[str]:
        """List all registered adapter names."""
        return list(self._adapters.keys())

    def get_healthy_adapter(
        self,
        mode: "OperatorMode | None" = None,
    ) -> ModelAdapter | None:
        """Get the first healthy adapter.

        If mode is specified, filters for adapters supporting that mode.
        """
        for adapter in self._adapters.values():
            if mode is not None and mode not in adapter.supported_modes:
                continue
            if adapter.health_check():
                return adapter
        return None

    def health_check_all(self) -> dict[str, bool]:
        """Check health of all registered adapters.

        Returns a dict mapping adapter names to health status.
        """
        return {
            name: adapter.health_check()
            for name, adapter in self._adapters.items()
        }

    def complete(
        self,
        prompt: str,
        config: ModelConfig | None = None,
        adapter_name: str | None = None,
    ) -> ModelResponse:
        """Complete using specified adapter or default.

        Args:
            prompt: Input prompt
            config: Model configuration
            adapter_name: Specific adapter to use, or None for default

        Returns:
            ModelResponse from the adapter

        Raises:
            RuntimeError: If no suitable adapter found
        """
        if adapter_name:
            adapter = self._adapters.get(adapter_name)
        else:
            adapter = self.get_default()

        if adapter is None:
            raise RuntimeError("No model adapter available")

        return adapter.complete(prompt, config)


# Global registry instance
_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    """Get the global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def register_adapter(
    name: str,
    adapter: ModelAdapter,
    set_default: bool = False,
) -> None:
    """Register an adapter with the global registry."""
    get_registry().register(name, adapter, set_default)


__all__ = [
    "ModelRegistry",
    "get_registry",
    "register_adapter",
]
