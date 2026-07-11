"""Shell provider — executes sandboxed shell commands with receipts and truth facts."""

from __future__ import annotations

import subprocess
import threading
from typing import TYPE_CHECKING, Any, Callable

from ai_command_center.core.command_sandbox import CommandSandbox, SecurityError
from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult

if TYPE_CHECKING:
    pass

_logger = __import__("logging").getLogger(__name__)

_active_shell_proc: subprocess.Popen[str] | None = None
_active_shell_lock = threading.Lock()


def _cancel_active_shell() -> bool:
    """Kill the in-flight shell subprocess, if any."""
    global _active_shell_proc
    with _active_shell_lock:
        proc = _active_shell_proc
    if proc is None or proc.poll() is not None:
        return False
    try:
        proc.kill()
        proc.wait(timeout=2.0)
        return True
    except Exception:
        _logger.exception("failed to kill active shell subprocess")
        return False


ShellRunFn = Callable[[str], dict[str, Any]]


def _default_run(command: str) -> dict[str, Any]:
    sandbox = CommandSandbox()
    try:
        argv = sandbox.validate_command(command)
    except SecurityError as exc:
        _logger.warning("shell command rejected by sandbox: %s", exc)
        return {"success": False, "error": str(exc)}
    try:
        with _active_shell_lock:
            proc = subprocess.Popen(
                argv,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            global _active_shell_proc
            _active_shell_proc = proc
        try:
            stdout, stderr = proc.communicate(timeout=30)
        finally:
            with _active_shell_lock:
                if _active_shell_proc is proc:
                    _active_shell_proc = None
        completed_stdout = (stdout or "").strip()
        completed_stderr = (stderr or "").strip()
        output = completed_stdout or completed_stderr
        if proc.returncode != 0 and not output:
            return {
                "success": False,
                "exit_code": proc.returncode,
                "output": "",
                "error": completed_stderr or f"exit code {proc.returncode}",
            }
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": output,
            "stdout": completed_stdout,
            "stderr": completed_stderr,
            "error": completed_stderr or None,
        }
    except subprocess.TimeoutExpired:
        _cancel_active_shell()
        return {"success": False, "error": "shell command timed out"}
    except OSError as exc:
        return {"success": False, "error": str(exc)}


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
