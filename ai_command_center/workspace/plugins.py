"""Plugin Architecture (Reference Architecture v3.5, Part VIII).

Plugins extend platform behavior without modifying core code. Discovery location
(runtime concern, not this layer): ``%APPDATA%\\AICommandCenter\\plugins\\``.

Execution model — **Tier 1: exclusive matching**, highest-priority match wins. This
is deterministic, simple, and predictable. Pipeline enrichment (Plugin A → B → C) is
an allowed *future* evolution for context augmentation only, never for execution;
fan-out execution is outside the approved baseline.
"""

from __future__ import annotations

from collections.abc import Iterable

from ai_command_center.workspace.domain import WorkspaceContext


class CommandPlugin:
    """Contract a plugin implements to participate in matching/enrichment/execution."""

    @property
    def name(self) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    @property
    def priority(self) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    def match(self, context: WorkspaceContext) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def enrich_context(self, context: WorkspaceContext) -> WorkspaceContext:
        # Default: identity. Override only for context augmentation, not execution.
        return context

    def execute(self, context: WorkspaceContext):  # pragma: no cover - interface
        raise NotImplementedError


class PluginRegistry:
    """Selects the single winning plugin via Tier-1 exclusive matching.

    Deterministic: among plugins whose ``match`` is true, the highest ``priority``
    wins; ties break by ``name``. A plugin raising during ``match`` is skipped so one
    faulty plugin cannot break selection.
    """

    def __init__(self, plugins: Iterable[CommandPlugin] = ()) -> None:
        self._plugins: list[CommandPlugin] = list(plugins)

    def register(self, plugin: CommandPlugin) -> None:
        self._plugins.append(plugin)

    def matching(self, context: WorkspaceContext) -> tuple[CommandPlugin, ...]:
        found: list[CommandPlugin] = []
        for plugin in self._plugins:
            try:
                if plugin.match(context):
                    found.append(plugin)
            except Exception:  # noqa: BLE001 - a faulty plugin must not break selection
                continue
        return tuple(sorted(found, key=lambda p: (-p.priority, p.name)))

    def select(self, context: WorkspaceContext) -> CommandPlugin | None:
        matches = self.matching(context)
        return matches[0] if matches else None

    def enrich(self, context: WorkspaceContext) -> WorkspaceContext:
        """Apply the winning plugin's context enrichment (no execution)."""
        plugin = self.select(context)
        if plugin is None:
            return context
        return plugin.enrich_context(context)
