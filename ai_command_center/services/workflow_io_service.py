"""Workflow YAML import/export — filesystem owned by the service, not the UI."""

from __future__ import annotations

import pathlib
from typing import Callable

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    WORKFLOW_EXPORT_ERROR,
    WORKFLOW_EXPORT_REQUEST,
    WORKFLOW_EXPORT_RESULT,
    WORKFLOW_IMPORT_ERROR,
    WORKFLOW_IMPORT_REQUEST,
    WORKFLOW_IMPORT_RESULT,
)
from ai_command_center.domain.workflow_definition import WorkflowDefinition
from ai_command_center.services.base import BaseService


class WorkflowIoService(BaseService):
    name = "workflow_io"

    def __init__(self, bus) -> None:
        super().__init__(bus)
        self._unsubs: list[Callable[[], None]] = []

    def _on_load(self) -> None:
        self._unsubs.append(
            self._bus.subscribe(WORKFLOW_EXPORT_REQUEST, self._on_export)
        )
        self._unsubs.append(
            self._bus.subscribe(WORKFLOW_IMPORT_REQUEST, self._on_import)
        )

    def _on_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_export(self, event: Event) -> None:
        payload = event.payload if isinstance(event.payload, dict) else {}
        path = str(payload.get("path") or "").strip()
        content = str(payload.get("yaml") or "")
        if not path:
            self._bus.publish(
                WORKFLOW_EXPORT_ERROR,
                {"message": "missing export path"},
                source=self.name,
            )
            return
        try:
            pathlib.Path(path).write_text(content, encoding="utf-8")
            self._bus.publish(
                WORKFLOW_EXPORT_RESULT,
                {"path": path},
                source=self.name,
            )
        except OSError as exc:
            self._bus.publish(
                WORKFLOW_EXPORT_ERROR,
                {"message": str(exc)},
                source=self.name,
            )

    def _on_import(self, event: Event) -> None:
        payload = event.payload if isinstance(event.payload, dict) else {}
        path = str(payload.get("path") or "").strip()
        if not path:
            self._bus.publish(
                WORKFLOW_IMPORT_ERROR,
                {"message": "missing import path"},
                source=self.name,
            )
            return
        try:
            yaml_content = pathlib.Path(path).read_text(encoding="utf-8")
            definition = WorkflowDefinition.from_yaml(yaml_content)
            self._bus.publish(
                WORKFLOW_IMPORT_RESULT,
                {
                    "path": path,
                    "workflow_id": definition.workflow_id,
                    "workflow_name": definition.workflow_name,
                    "yaml": yaml_content,
                },
                source=self.name,
            )
        except (OSError, ValueError) as exc:
            self._bus.publish(
                WORKFLOW_IMPORT_ERROR,
                {"message": str(exc)},
                source=self.name,
            )
