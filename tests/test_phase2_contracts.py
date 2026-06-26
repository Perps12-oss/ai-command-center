import unittest

from ai_command_center.core.app_state import AppStateStore
from ai_command_center.core.event_bus import EventBus
from ai_command_center.core.events.topics import SERVICE_READY, SERVICE_STARTED, SYSTEM_SNAPSHOT
from ai_command_center.services.base import BaseService
from ai_command_center.services.states import ServiceState


class DummyService(BaseService):
    name = "dummy"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.loaded = False

    def _on_load(self) -> None:
        self.loaded = True


class Phase2ContractTests(unittest.TestCase):
    def test_system_snapshot_updates_app_state(self) -> None:
        bus = EventBus()
        store = AppStateStore(bus)
        bus.publish(
            SYSTEM_SNAPSHOT,
            {
                "phase": "ready",
                "cpu_percent": 42.0,
                "ram_percent": 77.0,
                "tool_count": 3,
                "service_states": (("dummy", "ready"),),
            },
            source="tests",
        )
        snapshot = store.snapshot.system_snapshot
        self.assertEqual("ready", snapshot.phase)
        self.assertEqual(42.0, snapshot.cpu_percent)
        self.assertEqual(77.0, snapshot.ram_percent)
        self.assertEqual(3, snapshot.tool_count)

    def test_base_service_start_emits_lifecycle_events(self) -> None:
        bus = EventBus()
        service = DummyService(bus)
        events: list[str] = []

        bus.subscribe(SERVICE_STARTED, lambda event: events.append(event.topic))
        bus.subscribe(SERVICE_READY, lambda event: events.append(event.topic))

        service.start()

        self.assertTrue(service.loaded)
        self.assertEqual(ServiceState.READY, service.state)
        self.assertEqual(service.get_state(), "ready")
        self.assertEqual([SERVICE_STARTED, SERVICE_READY], events)


if __name__ == "__main__":
    unittest.main()
