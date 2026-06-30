"""Risk area #2 - AppState immutability.

AppState is a frozen dataclass, so any direct attribute assignment must raise.
State may change *only* by republishing events through the store's reducers.
"""

from __future__ import annotations

import dataclasses

import pytest

from ai_command_center.core.app_state import AppState, AppStateStore
from ai_command_center.core.events.topics import APP_PHASE


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("phase", "chat"),
        ("chat_status", "streaming"),
        ("last_command", "do thing"),
        ("settings_version", 99),
    ],
)
def test_direct_mutation_is_rejected(field_name: str, value: object) -> None:
    state = AppState()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)) as exc:
        setattr(state, field_name, value)
    assert field_name in str(exc.value) or "frozen" in str(exc.value).lower(), (
        f"mutating AppState.{field_name} should fail loudly, got: {exc.value}"
    )


def test_cannot_add_new_attribute() -> None:
    state = AppState()
    # frozen + slots rejects unknown attributes (FrozenInstanceError / AttributeError /
    # TypeError depending on interpreter version) - the point is it never succeeds.
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError, TypeError)):
        state.surprise_attribute = True  # type: ignore[attr-defined]


def test_store_snapshot_is_immutable_but_reducers_update_state(event_bus) -> None:
    store = AppStateStore(event_bus)
    try:
        before = store.snapshot
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            before.phase = "hacked"  # type: ignore[misc]

        event_bus.publish(APP_PHASE, {"phase": "ready"}, source="test")
        after = store.snapshot

        assert after is not before, "store must replace the snapshot, not mutate it"
        assert after.phase == "ready", "reducer-driven update should take effect"
        assert before.phase != "ready", "original snapshot must be unaffected"
    finally:
        store.close()
