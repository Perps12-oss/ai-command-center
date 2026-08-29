"""Shared sandboxed subprocess runner (single implementation for tool + latent paths).

Live OS side effects for tools still enter via TOOL_INVOKE → ToolExecutorService.
This module only owns validate + Popen + communicate + cancel so ShellProvider
and ToolExecutor cannot drift.
"""

from __future__ import annotations

import logging
import subprocess
import threading
from typing import Any

from ai_command_center.core.command_sandbox import CommandSandbox, SecurityError

logger = logging.getLogger(__name__)

_active_shell_proc: subprocess.Popen[str] | None = None
_active_shell_lock = threading.Lock()

DEFAULT_TIMEOUT_S = 30.0


def cancel_active_shell() -> bool:
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
        logger.exception("failed to kill active shell subprocess")
        return False


def run_sandboxed_command(
    command: str,
    sandbox: CommandSandbox,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Validate and run ``command`` with ``shell=False``. Returns a result dict."""
    global _active_shell_proc
    cleaned = str(command or "").strip()
    if not cleaned:
        return {"success": False, "output": "", "error": "empty shell command"}
    try:
        argv = sandbox.validate_command(cleaned)
    except SecurityError as exc:
        logger.warning("shell command rejected by sandbox: %s", exc)
        return {"success": False, "output": "", "error": str(exc)}
    try:
        with _active_shell_lock:
            proc = subprocess.Popen(
                argv,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            _active_shell_proc = proc
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
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
                "stdout": completed_stdout,
                "stderr": completed_stderr,
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
        cancel_active_shell()
        return {"success": False, "output": "", "error": "shell command timed out"}
    except OSError as exc:
        return {"success": False, "output": "", "error": str(exc)}
