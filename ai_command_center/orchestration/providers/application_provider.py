"""Application launch provider — open desktop applications with receipts."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from typing import Any

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult

_logger = logging.getLogger(__name__)

_APP_COMMANDS: dict[str, list[str]] = {
    "outlook": ["cmd", "/c", "start", "", "outlook"],
    "notepad": ["notepad"],
    "calculator": ["calc"],
}

LaunchFn = Callable[[str, list[str]], dict[str, Any]]


def _default_launch(application: str, argv: list[str]) -> dict[str, Any]:
    try:
        subprocess.Popen(argv, shell=False)
        return {"application": application, "launched": True}
    except OSError as exc:
        _logger.warning("application launch failed app=%s error=%s", application, exc)
        return {"application": application, "launched": False, "error": str(exc)}


class ApplicationProvider:
    """Launches whitelisted desktop applications."""

    provider_id = "application"

    def __init__(self, *, launch_fn: LaunchFn | None = None) -> None:
        self._launch_fn = launch_fn or _default_launch

    def health(self) -> tuple[bool, str]:
        return True, "ready"

    def execute(
        self,
        intent: OrchestrationIntent,
        *,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> ProviderExecutionResult:
        if intent is not OrchestrationIntent.LAUNCH_APPLICATION:
            return ProviderExecutionResult(
                success=False,
                error=f"unsupported intent: {intent.value}",
            )
        application = str(args.get("application", "")).strip().lower()
        if application == "calc":
            application = "calculator"
        argv = _APP_COMMANDS.get(application)
        if not argv:
            return ProviderExecutionResult(
                success=False,
                error=f"unsupported application: {application}",
            )

        outcome = self._launch_fn(application, list(argv))
        launched = bool(outcome.get("launched"))
        error = str(outcome.get("error", "")).strip() or None
        if not launched and error is None:
            error = "launch failed"

        facts: dict[str, object] = {
            "application": application,
            "launched": launched,
            "argv": argv,
        }
        if error:
            facts["error"] = error

        if launched:
            return ProviderExecutionResult(
                success=True,
                response_text=f"Opened {application}.",
                facts=facts,
            )
        return ProviderExecutionResult(
            success=False,
            response_text="",
            facts=facts,
            error=error,
        )
