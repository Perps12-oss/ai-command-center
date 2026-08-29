"""Shell provider — executes sandboxed shell commands with receipts and truth facts.

Latent / paper orchestration path. Live shell side effects enter via
TOOL_INVOKE → ToolExecutorService. This provider shares ``run_sandboxed_command``
so allowlist/Popen/cancel cannot drift.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from ai_command_center.core.command_sandbox import (
    ORCHESTRATION_SHELL_ALLOWLIST,
    CommandSandbox,
)
from ai_command_center.core.sandboxed_shell import run_sandboxed_command
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult

if TYPE_CHECKING:
    pass

_logger = __import__("logging").getLogger(__name__)

_ORCH_SANDBOX = CommandSandbox(allowlist=ORCHESTRATION_SHELL_ALLOWLIST)

ShellRunFn = Callable[[str], dict[str, Any]]


def _default_run(command: str) -> dict[str, Any]:
    # Explicit policy — never the library default (which historically admitted
    # interpreters). Approval for WRITE_DESTROY must match what can actually run.
    return run_sandboxed_command(command, _ORCH_SANDBOX)


class ShellProvider:
    """Executes sandboxed shell commands via OrchestrationExecutor with receipts."""

    provider_id = "shell"

    def __init__(
        self,
        *,
        run_fn: ShellRunFn | None = None,
    ) -> None:
        self._run_fn = run_fn or _default_run

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
        if intent is not OrchestrationIntent.EXECUTE_SHELL:
            return ProviderExecutionResult(
                success=False,
                error=f"unsupported intent: {intent.value}",
            )
        command = str(args.get("command", "")).strip()
        if not command:
            return ProviderExecutionResult(
                success=False,
                error="empty shell command",
            )

        outcome = self._run_fn(command)
        success = bool(outcome.get("success"))
        error = str(outcome.get("error", "")).strip() or None
        output = str(outcome.get("output", "")).strip()
        exit_code = outcome.get("exit_code")

        facts: dict[str, object] = {
            "command": command,
            "success": success,
            "output": output,
        }
        if exit_code is not None:
            facts["exit_code"] = exit_code
        stdout_val = outcome.get("stdout")
        if stdout_val:
            facts["stdout"] = stdout_val
        stderr_val = outcome.get("stderr")
        if stderr_val:
            facts["stderr"] = stderr_val
        if error:
            facts["error"] = error

        if success:
            return ProviderExecutionResult(
                success=True,
                response_text=output or f"Command completed: {command}",
                facts=facts,
            )
        return ProviderExecutionResult(
            success=False,
            response_text=output,
            facts=facts,
            error=error,
        )
