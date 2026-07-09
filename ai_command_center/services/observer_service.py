"""Brain observer framework: startup sync plus throttled local monitoring."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from ai_command_center.core.events.topics import (
    OBSERVATION_BATCH_RECEIVED,
    OBSERVATION_FAILED,
    OBSERVATION_RECEIVED,
    OBSERVER_ERROR,
    OBSERVER_STARTED,
    OBSERVER_STOPPED,
)
from ai_command_center.domain.correlation import CorrelationContext
from ai_command_center.domain.observation import (
    Observation,
    ObservationChangeType,
    ObservationMode,
    ObservationSource,
)
from ai_command_center.services.base import BaseService


class FileSystemObserver:
    """Local filesystem observer hidden behind the observer contract."""

    def __init__(self, roots: list[Path], *, max_entries: int = 500) -> None:
        self._roots = roots
        self._max_entries = max_entries
        self._seen: dict[str, float] = {}

    @property
    def name(self) -> str:
        return "filesystem"

    def snapshot(self, correlation: CorrelationContext) -> list[Observation]:
        observations: list[Observation] = []
        for root in self._roots:
            if not root.exists():
                observations.append(
                    Observation(
                        id=uuid.uuid4().hex,
                        source=ObservationSource.FILESYSTEM,
                        mode=ObservationMode.STARTUP_SYNC,
                        subject=str(root),
                        change_type=ObservationChangeType.ERROR,
                        raw_payload={"error": "root does not exist"},
                        correlation=correlation,
                    )
                )
                continue
            for path in _walk_bounded(root, self._max_entries - len(observations)):
                stat = path.stat()
                key = str(path)
                self._seen[key] = stat.st_mtime
                observations.append(
                    Observation(
                        id=uuid.uuid4().hex,
                        source=ObservationSource.FILESYSTEM,
                        mode=ObservationMode.STARTUP_SYNC,
                        subject=key,
                        change_type=ObservationChangeType.SNAPSHOT,
                        raw_payload={
                            "path": key,
                            "is_file": path.is_file(),
                            "size": stat.st_size if path.is_file() else 0,
                            "mtime": stat.st_mtime,
                        },
                        correlation=correlation,
                    )
                )
                if len(observations) >= self._max_entries:
                    break
        return observations

    def poll(self, correlation: CorrelationContext) -> list[Observation]:
        observations: list[Observation] = []
        current: dict[str, float] = {}
        for root in self._roots:
            if not root.exists():
                continue
            for path in _walk_bounded(root, self._max_entries - len(current)):
                stat = path.stat()
                key = str(path)
                current[key] = stat.st_mtime
                prior = self._seen.get(key)
                if prior is None:
                    change = ObservationChangeType.CREATED
                elif stat.st_mtime > prior:
                    change = ObservationChangeType.UPDATED
                else:
                    continue
                observations.append(
                    Observation(
                        id=uuid.uuid4().hex,
                        source=ObservationSource.FILESYSTEM,
                        mode=ObservationMode.CONTINUOUS,
                        subject=key,
                        change_type=change,
                        raw_payload={
                            "path": key,
                            "is_file": path.is_file(),
                            "mtime": stat.st_mtime,
                        },
                        correlation=correlation,
                    )
                )
        for key in set(self._seen) - set(current):
            observations.append(
                Observation(
                    id=uuid.uuid4().hex,
                    source=ObservationSource.FILESYSTEM,
                    mode=ObservationMode.CONTINUOUS,
                    subject=key,
                    change_type=ObservationChangeType.DELETED,
                    raw_payload={"path": key},
                    correlation=correlation,
                )
            )
        self._seen = current
        return observations


class ClipboardObserver:
    """Explicit clipboard observer hook; caller supplies a local provider."""

    def __init__(self, provider: Callable[[], str] | None = None) -> None:
        self._provider = provider
        self._last = ""

    @property
    def name(self) -> str:
        return "clipboard"

    def snapshot(self, correlation: CorrelationContext) -> list[Observation]:
        if self._provider is None:
            return []
        value = self._provider()
        self._last = value
        if not value:
            return []
        return [
            Observation(
                id=uuid.uuid4().hex,
                source=ObservationSource.CLIPBOARD,
                mode=ObservationMode.STARTUP_SYNC,
                subject="clipboard",
                change_type=ObservationChangeType.SNAPSHOT,
                raw_payload={"text": value},
                correlation=correlation,
            )
        ]


class ObserverService(BaseService):
    """Runs startup sync and optional throttled filesystem monitoring."""

    name = "observer"

    def __init__(
        self,
        bus,
        *,
        filesystem_roots: list[Path] | None = None,
        clipboard_provider: Callable[[], str] | None = None,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        super().__init__(bus)
        self._filesystem = FileSystemObserver(filesystem_roots or [])
        self._clipboard = ClipboardObserver(clipboard_provider)
        self._poll_interval_seconds = poll_interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _on_load(self) -> None:
        correlation = CorrelationContext.new(action_id="observer-startup-sync")
        self._bus.publish(
            OBSERVER_STARTED,
            {"observer": self._filesystem.name, "correlation": correlation.to_payload()},
            source=self.name,
        )
        self._publish_batch(self._filesystem.snapshot(correlation))
        self._publish_batch(self._clipboard.snapshot(correlation))
        if self._filesystem_roots_enabled:
            self._thread = threading.Thread(
                target=self._poll_loop,
                name="brain-observer-poll",
                daemon=True,
            )
            self._thread.start()

    def _on_unload(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._bus.publish(OBSERVER_STOPPED, {"observer": "filesystem"}, source=self.name)

    @property
    def _filesystem_roots_enabled(self) -> bool:
        return bool(self._filesystem._roots)

    def _poll_loop(self) -> None:
        while not self._stop.wait(self._poll_interval_seconds):
            correlation = CorrelationContext.new(action_id="observer-poll")
            try:
                self._publish_batch(self._filesystem.poll(correlation))
            except Exception as exc:
                self._bus.publish(
                    OBSERVER_ERROR,
                    {
                        "observer": "filesystem",
                        "error": str(exc),
                        "correlation": correlation.to_payload(),
                    },
                    source=self.name,
                )

    def _publish_batch(self, observations: list[Observation]) -> None:
        if not observations:
            return
        payloads = [item.to_payload() for item in observations]
        self._bus.publish(
            OBSERVATION_BATCH_RECEIVED,
            {"observations": payloads},
            source=self.name,
        )
        for payload in payloads:
            topic = (
                OBSERVATION_FAILED
                if payload["change_type"] == ObservationChangeType.ERROR.value
                else OBSERVATION_RECEIVED
            )
            self._bus.publish(topic, payload, source=self.name)


def _walk_bounded(root: Path, limit: int) -> list[Path]:
    if limit <= 0:
        return []
    paths: list[Path] = []
    if root.is_file():
        return [root]
    for path in root.rglob("*"):
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths
