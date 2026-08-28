"""Auto-bootstrap a workspace for deferred first commands.

When ExecutionAuthority emits ``ui.workspace.required`` because no active
workspace exists, this service creates/selects a default workspace and replays
the deferred command via ``ui.command.replay`` (async-eligible) → ``ui.command``.

Bootstrap is an explicit state machine with an identity (``bootstrap_id``):

    IDLE ──ui.workspace.required──▶ IN_FLIGHT(bootstrap_id=X)
      ▲                                │
      │                                ├─ workspace.create.result(X, ok)
      │                                │     └─ replay X's deferred commands
      │                                │        into X's workspace only
      ├─ workspace.create.result(X, error) ──▶ FAILED (queue discarded)
      └─ timeout ─────────────────────────▶ FAILED (queue discarded)

Only the result carrying the in-flight ``bootstrap_id`` resolves the attempt,
so an unrelated workspace activation can never authorize replay of commands
issued for a different context. Transitions arrive on bus threads and on the
timeout timer thread, so exactly one of them may claim an attempt: whoever
claims it owns its deferred commands.

Replay is published on ``ui.command.replay`` (ASYNC_ELIGIBLE) so it never
nests a second ``ui.command`` inside the original SYNC_CRITICAL intake stack.
Duplicate ``request_id`` values are ignored once seen (pending or replayed).
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

from ai_command_center.core.event_bus import Event
from ai_command_center.core.events.topics import (
    APP_ERROR,
    APP_WARNING,
    UI_COMMAND,
    UI_COMMAND_REPLAY,
    UI_CREATE_WORKSPACE,
    UI_WORKSPACE_REQUIRED,
    WORKSPACE_ACTIVE,
    WORKSPACE_CREATE_RESULT,
    WORKSPACE_DEACTIVATED,
)
from ai_command_center.services.base import BaseService

logger = logging.getLogger(__name__)

_DEFAULT_WORKSPACE_TITLE = "My Workspace"
_DEFAULT_WORKSPACE_DESCRIPTION = "Auto-created to run your first command."

# A wedged bootstrap must not queue commands forever.
BOOTSTRAP_TIMEOUT_S = 15.0
MAX_PENDING_COMMANDS = 8
MAX_SEEN_REQUEST_IDS = 64


@dataclass
class _Bootstrap:
    """One bootstrap attempt: identity, its deferred commands, its workspace."""

    bootstrap_id: str
    commands: list[dict[str, str]] = field(default_factory=list)
    workspace_id: str = ""
    timer: threading.Timer | None = None


class WorkspaceBootstrapService(BaseService):
    """Creates/selects a default workspace and replays deferred commands."""

    name = "workspace_bootstrap"

    def __init__(self, bus, *, timeout_s: float = BOOTSTRAP_TIMEOUT_S) -> None:
        super().__init__(bus)
        self._unsubscribers: list[Callable[[], None]] = []
        self._active_workspace_id: str = ""
        self._timeout_s = timeout_s
        self._lock = threading.RLock()
        self._bootstrap: _Bootstrap | None = None
        # Bounded set of request_ids already queued or replayed this session.
        self._seen_request_ids: OrderedDict[str, None] = OrderedDict()

    def _on_load(self) -> None:
        self._unsubscribers.append(
            self._bus.subscribe(UI_WORKSPACE_REQUIRED, self._on_workspace_required)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_ACTIVE, self._on_workspace_active)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_DEACTIVATED, self._on_workspace_deactivated)
        )
        self._unsubscribers.append(
            self._bus.subscribe(WORKSPACE_CREATE_RESULT, self._on_workspace_create_result)
        )
        self._unsubscribers.append(
            self._bus.subscribe(UI_COMMAND_REPLAY, self._on_command_replay)
        )

    def _on_unload(self) -> None:
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self._take_bootstrap()
        self._active_workspace_id = ""
        with self._lock:
            self._seen_request_ids.clear()

    @property
    def bootstrap_inflight(self) -> bool:
        return self._bootstrap is not None

    @property
    def pending_command_count(self) -> int:
        with self._lock:
            return len(self._bootstrap.commands) if self._bootstrap else 0

    def _remember_request_id(self, request_id: str) -> bool:
        """Return True when ``request_id`` is newly seen; False if duplicate.

        Empty ids are treated as unique (no correlation to dedupe on).
        """
        if not request_id:
            return True
        with self._lock:
            if request_id in self._seen_request_ids:
                return False
            self._seen_request_ids[request_id] = None
            while len(self._seen_request_ids) > MAX_SEEN_REQUEST_IDS:
                self._seen_request_ids.popitem(last=False)
            return True

    def _take_bootstrap(self, bootstrap_id: str = "") -> _Bootstrap | None:
        """Claim the in-flight attempt, or None when another thread claimed it.

        A terminal transition (resolve, failure, timeout) must happen once:
        claiming the attempt hands its deferred commands to exactly one caller,
        so a create result landing as the timeout fires cannot both replay and
        fail the same command.
        """
        with self._lock:
            bootstrap = self._bootstrap
            if bootstrap is None:
                return None
            if bootstrap_id and bootstrap.bootstrap_id != bootstrap_id:
                return None
            self._bootstrap = None
        if bootstrap.timer is not None:
            bootstrap.timer.cancel()
        return bootstrap

    def _on_workspace_active(self, event: Event) -> None:
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        if not workspace_id:
            return
        self._active_workspace_id = workspace_id
        with self._lock:
            bootstrap = self._bootstrap
            # Only the workspace this bootstrap created authorizes replay.
            if bootstrap is None or bootstrap.workspace_id != workspace_id:
                return
            bootstrap_id = bootstrap.bootstrap_id
        self._resolve_bootstrap(workspace_id, bootstrap_id=bootstrap_id)

    def _on_workspace_deactivated(self, event: Event) -> None:
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        if not workspace_id or workspace_id == self._active_workspace_id:
            self._active_workspace_id = ""

    def _on_workspace_create_result(self, event: Event) -> None:
        # A workspace created for some other reason never resolves this attempt.
        bootstrap_id = str(event.payload.get("bootstrap_id", "")).strip()
        if not bootstrap_id:
            return
        error = str(event.payload.get("error", "")).strip()
        if error:
            self._fail_bootstrap(
                f"Could not create a workspace: {error}",
                bootstrap_id=bootstrap_id,
            )
            return
        workspace_id = str(event.payload.get("workspace_id", "")).strip()
        if not workspace_id:
            self._fail_bootstrap(
                "Workspace creation returned no workspace id.",
                bootstrap_id=bootstrap_id,
            )
            return
        with self._lock:
            bootstrap = self._bootstrap
            if bootstrap is not None and bootstrap.bootstrap_id == bootstrap_id:
                bootstrap.workspace_id = workspace_id
        # The creating handler activates the workspace it created, so the
        # matching result is the authorization to replay.
        self._resolve_bootstrap(workspace_id, bootstrap_id=bootstrap_id)

    def _on_workspace_required(self, event: Event) -> None:
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        request_id = str(event.payload.get("request_id", "")).strip()
        if not self._remember_request_id(request_id):
            logger.info(
                "workspace_bootstrap.duplicate_ignored request_id=%s",
                request_id,
            )
            return
        command = {"text": text, "request_id": request_id}

        if self._active_workspace_id:
            self._replay([command], self._active_workspace_id)
            return

        with self._lock:
            bootstrap = self._bootstrap
            if bootstrap is None:
                bootstrap = _Bootstrap(bootstrap_id=uuid.uuid4().hex, commands=[command])
                self._bootstrap = bootstrap
            else:
                self._enqueue(bootstrap, command)
                return
        if self._timeout_s > 0:
            bootstrap.timer = threading.Timer(
                self._timeout_s,
                self._on_bootstrap_timeout,
                args=(bootstrap.bootstrap_id,),
            )
            bootstrap.timer.daemon = True
            bootstrap.timer.start()
        logger.info(
            "workspace_bootstrap.started bootstrap_id=%s request_id=%s",
            bootstrap.bootstrap_id,
            request_id,
        )
        self._bus.publish(
            UI_CREATE_WORKSPACE,
            {
                "title": _DEFAULT_WORKSPACE_TITLE,
                "description": _DEFAULT_WORKSPACE_DESCRIPTION,
                "bootstrap_id": bootstrap.bootstrap_id,
            },
            source=self.name,
        )

    def _enqueue(self, bootstrap: _Bootstrap, command: dict[str, str]) -> None:
        """Append under ``self._lock``, shedding the oldest past the bound."""
        bootstrap.commands.append(command)
        while len(bootstrap.commands) > MAX_PENDING_COMMANDS:
            dropped = bootstrap.commands.pop(0)
            logger.warning(
                "workspace_bootstrap.pending_overflow bootstrap_id=%s dropped_request_id=%s",
                bootstrap.bootstrap_id,
                dropped.get("request_id", ""),
            )
            self._bus.publish(
                APP_WARNING,
                {
                    "message": (
                        "Too many commands are waiting for a workspace; "
                        "the oldest was discarded."
                    ),
                    "request_id": dropped.get("request_id", ""),
                },
                source=self.name,
            )

    def _on_bootstrap_timeout(self, bootstrap_id: str) -> None:
        self._fail_bootstrap("Workspace creation timed out.", bootstrap_id=bootstrap_id)

    def _fail_bootstrap(self, message: str, *, bootstrap_id: str = "") -> None:
        bootstrap = self._take_bootstrap(bootstrap_id)
        if bootstrap is None:
            return
        pending = list(bootstrap.commands)
        # Failed ids may be retried by the user; forget them so a new command
        # with the same request_id is not silently dropped.
        with self._lock:
            for item in pending:
                rid = item.get("request_id", "")
                if rid:
                    self._seen_request_ids.pop(rid, None)
        logger.error(
            "workspace_bootstrap.failed bootstrap_id=%s pending=%d detail=%s",
            bootstrap.bootstrap_id,
            len(pending),
            message,
        )
        for item in pending:
            payload: dict[str, object] = {
                "message": f"{message} Your command was not run.",
            }
            if item.get("request_id"):
                payload["request_id"] = item["request_id"]
            self._bus.publish(APP_ERROR, payload, source=self.name)
        if not pending:
            self._bus.publish(APP_ERROR, {"message": message}, source=self.name)

    def _resolve_bootstrap(self, workspace_id: str, *, bootstrap_id: str = "") -> None:
        bootstrap = self._take_bootstrap(bootstrap_id)
        if bootstrap is None:
            return
        self._replay(list(bootstrap.commands), workspace_id)

    def _replay(self, commands: list[dict[str, str]], workspace_id: str) -> None:
        """Queue replay off the SYNC_CRITICAL ``ui.command`` stack."""
        for item in commands:
            payload: dict[str, object] = {
                "text": item["text"],
                "replayed_from_workspace_bootstrap": True,
                "bootstrap_workspace_id": workspace_id,
            }
            request_id = item.get("request_id", "")
            if request_id:
                payload["request_id"] = request_id
            self._bus.publish(UI_COMMAND_REPLAY, payload, source=self.name)

    def _on_command_replay(self, event: Event) -> None:
        """Promote an async replay envelope into intake ``ui.command``."""
        text = str(event.payload.get("text", "")).strip()
        if not text:
            return
        payload = dict(event.payload)
        payload["text"] = text
        self._bus.publish(UI_COMMAND, payload, source=self.name)
