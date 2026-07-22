"""Component tests for the OS Palette and palette providers."""

from __future__ import annotations

import pytest

from ai_command_center.core.app_state import AppState, WorkspaceOsEntity, WorkspaceOsSnapshot
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import PALETTE_PROVIDER_REGISTER, UI_PALETTE_ACTION
from ai_command_center.ui.controller import UIController
from ai_command_center.ui.design_system.palette_provider import (
    PaletteCommand,
    StaticPaletteProvider,
    WorkspaceOSPaletteProvider,
)
from tests.ui.fake_ui import OSPalette


class _FakeMaster:
    def winfo_x(self) -> int:
        return 0

    def winfo_y(self) -> int:
        return 0

    def winfo_width(self) -> int:
        return 1100


@pytest.fixture
def palette():
    """Return a fake-bound OSPalette instance."""
    return OSPalette(_FakeMaster())


def test_os_palette_filters_and_executes(palette):
    """OSPalette filters commands by label/description and executes the selected action."""
    seen: list[str] = []
    commands = [
        PaletteCommand("First", "Desc one", lambda: seen.append("one"), section="A"),
        PaletteCommand("Second", "Desc two", lambda: seen.append("two"), section="B"),
    ]
    palette.show(commands)
    palette._filter("sec")
    assert len(palette._filtered) == 1
    assert palette._filtered[0].label == "Second"
    palette._execute(0)
    assert seen == ["two"]


def test_os_palette_renders_sections(palette):
    """Commands from different sections produce section headers."""
    commands = [
        PaletteCommand("Nav A", "nav", section="Navigation"),
        PaletteCommand("Nav B", "nav", section="Navigation"),
        PaletteCommand("Act A", "action", section="Actions"),
    ]
    palette.show(commands)
    # Rendering populates _list_frame children via pack; children are tracked on the fake frame.
    children = palette._list_frame.winfo_children()
    labels = [c._kwargs.get("text", "") for c in children if c._kwargs.get("text")]
    assert "Navigation" in labels
    assert "Actions" in labels


def test_static_palette_provider_returns_commands():
    """StaticPaletteProvider returns the commands it was initialized with."""
    commands = [
        PaletteCommand("One", "First", section="A"),
        PaletteCommand("Two", "Second", section="B"),
    ]
    provider = StaticPaletteProvider(commands=commands, name="Test", priority=5)
    assert provider.get_commands(AppState()) == commands
    assert provider.priority == 5


def test_workspace_os_palette_provider_builds_commands():
    """WorkspaceOSPaletteProvider creates chat and launch commands for entities."""
    entity = WorkspaceOsEntity(
        entity_id="ent-1",
        entity_type="resource",
        title="My Resource",
        metadata=(
            ("resource_type", "file"),
            ("path", "/tmp/foo"),
            ("description", "A test resource"),
        ),
    )
    snap = AppState(workspace_os=WorkspaceOsSnapshot(entities=(entity,)))

    seen: list[tuple[str, dict]] = []
    provider = WorkspaceOSPaletteProvider(
        get_entities=lambda s: s.workspace_os.entities,
        on_open_chat=lambda p: seen.append(("chat", p)),
        on_launch=lambda p: seen.append(("launch", p)),
    )
    commands = provider.get_commands(snap)
    assert len(commands) == 2

    chat_cmd = commands[0]
    assert "Chat" in chat_cmd.label
    chat_cmd.action()
    assert seen[-1][0] == "chat"
    assert seen[-1][1]["entity_id"] == "ent-1"

    launch_cmd = commands[1]
    assert "🚀" in launch_cmd.label
    launch_cmd.action()
    assert seen[-1][0] == "launch"
    assert seen[-1][1]["resource_type"] == "file"


def test_ui_controller_palette_registry_aggregates_providers():
    """UIController registers providers and aggregates their commands."""
    bus = EventBus()
    from ai_command_center.core.app_state import AppStateStore

    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)

    controller.register_palette_provider(
        StaticPaletteProvider(
            commands=[PaletteCommand("A", "alpha", section="Test")],
            name="P1",
            priority=10,
        )
    )
    controller.register_palette_provider(
        StaticPaletteProvider(
            commands=[PaletteCommand("B", "beta", section="Test")],
            name="P2",
            priority=5,
        )
    )

    commands = controller.get_palette_commands(store.snapshot)
    assert len(commands) == 2
    assert commands[0].label == "B"  # lower priority first
    assert commands[1].label == "A"


def test_ui_controller_register_publishes_provider_event():
    """Registering a provider publishes PALETTE_PROVIDER_REGISTER on the bus."""
    bus = EventBus()
    from ai_command_center.core.app_state import AppStateStore

    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)

    seen: list[str] = []
    bus.subscribe(PALETTE_PROVIDER_REGISTER, lambda e: seen.append(str(e.payload.get("provider_name"))))

    controller.register_palette_provider(StaticPaletteProvider(name="MyProvider"))
    assert seen == ["MyProvider"]


def test_ui_controller_publish_palette_action():
    """UIController can publish a UI_PALETTE_ACTION event."""
    bus = EventBus()
    from ai_command_center.core.app_state import AppStateStore

    store = AppStateStore(bus)
    controller = UIController(bus, store, lambda: None)

    seen: list[dict] = []
    bus.subscribe(UI_PALETTE_ACTION, lambda e: seen.append(dict(e.payload)))

    controller.publish_palette_action("cmd-1", {"foo": "bar"})
    assert len(seen) == 1
    assert seen[0]["command_id"] == "cmd-1"
    assert seen[0]["payload"] == {"foo": "bar"}
