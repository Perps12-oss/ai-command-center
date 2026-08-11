"""A3 — executable receipt-coverage gate.

Proves every live OS side-effect call site in ``ai_command_center/`` is either:

  * inside the execution boundary — only reachable by the sole ``TOOL_INVOKE``
    publisher, therefore receipted (or failed closed) by ExecutionOrchestrator; or
  * on an explicit, severity-annotated allowlist of bypasses that the audit
    placed out of Phase A scope.

A **new** side-effect call site in an unlisted module fails the build. This is
enumerative on purpose: a test that only checks the two known-good paths would
not catch a newly introduced bypass.

Uses AST, not regex — a docstring mentioning ``subprocess.run`` is not a call.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "ai_command_center"

# Callables that produce an uncontained OS side effect.
_SIDE_EFFECT_ATTRS: dict[str, frozenset[str]] = {
    "subprocess": frozenset(
        {"run", "Popen", "call", "check_call", "check_output"}
    ),
    "os": frozenset({"startfile", "system", "execv", "execvp", "spawnl", "spawnv"}),
    "webbrowser": frozenset({"open", "open_new", "open_new_tab"}),
}

# Modules whose side effects execute only below the execution boundary: they are
# invoked by ToolExecutorService in response to TOOL_INVOKE, whose sole publisher
# is ExecutionOrchestratorService (ADR-018). Every such run yields an
# ExecutionReceipt + TruthBoundary validation, or fails closed (G1).
_BOUNDARY_MODULES: frozenset[str] = frozenset(
    {
        # The executor itself — runs shell tools dispatched via TOOL_INVOKE.
        "services/tool_executor_service.py",
        # Capability providers behind builtin tools.
        "orchestration/providers/shell_provider.py",
        "orchestration/providers/application_provider.py",
        # G2: workspace launches, dispatched as workspace_* tools.
        "orchestration/workspace_launch_tools.py",
        # Frozen Phase 2 launch handlers. Reached only through
        # workspace_launch_tools (inside the boundary). The ActionRegistry route
        # is locked shut by test_no_action_registry_launch_bypass below.
        "core/workspace_os_actions.py",
    }
)

# Known bypasses, deliberately NOT fixed in Phase A. Severity from the audit's
# Runtime Bypass Register. Each entry is a standing debt, not an exemption for
# new code: adding a module here is a deliberate, reviewable act.
_ALLOWLISTED_BYPASSES: dict[str, str] = {
    # Audit bypass #2 — chat export writes a file and may os.startfile it.
    "ui/shell/application_shell.py": "MEDIUM — chat export open; out of Phase A scope",
    # Audit bypass #3 — Runtime Inspector opens docs in a browser.
    "ui/runtime_inspector.py": "LOW — inspector webbrowser.open; out of Phase A scope",
    # Audit bypass #4 — QwenPaw sidecar process spawn.
    "services/qwenpaw_sidecar_service.py": "MEDIUM — sidecar Popen; out of Phase A scope",
    # G7 — external/mcp.* handlers, gated behind Goose Stage 3.
    "orchestration/providers/mcp_client.py": "MEDIUM — MCP stdio spawn; Goose Stage 3 gated",
    # Platform stub, Phase 11 backlog (not composed in the live runtime).
    "platform/linux/hotkey_provider.py": "LOW — Phase 11 platform stub; not live",
    # Read-only host identity probe; no user-facing side effect.
    "runtime_identity.py": "LOW — read-only identity probe",
}


def _iter_side_effect_sites() -> list[tuple[str, int, str]]:
    """Return (relative_module, lineno, "subprocess.run") for every call site."""
    sites: list[tuple[str, int, str]] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        rel = path.relative_to(PACKAGE_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            owner = func.value
            if not isinstance(owner, ast.Name):
                continue
            attrs = _SIDE_EFFECT_ATTRS.get(owner.id)
            if attrs and func.attr in attrs:
                sites.append((rel, node.lineno, f"{owner.id}.{func.attr}"))
    return sites


def test_every_side_effect_site_is_bounded_or_allowlisted() -> None:
    """No un-triaged OS side effect may exist in the package."""
    unaccounted = [
        (module, lineno, call)
        for module, lineno, call in _iter_side_effect_sites()
        if module not in _BOUNDARY_MODULES and module not in _ALLOWLISTED_BYPASSES
    ]
    assert not unaccounted, (
        "New OS side-effect call site(s) outside the execution boundary:\n"
        + "\n".join(f"  {m}:{n}  {c}" for m, n, c in unaccounted)
        + "\n\nEither route it through TOOL_INVOKE (so it is receipted), or add it "
        "to _ALLOWLISTED_BYPASSES with a severity and a reason."
    )


def test_gate_actually_sees_the_known_side_effects() -> None:
    """Guard against the gate silently matching nothing (e.g. a broken walker)."""
    sites = _iter_side_effect_sites()
    modules = {module for module, _, _ in sites}
    assert "core/workspace_os_actions.py" in modules, (
        "gate failed to detect the frozen workspace launch handlers — walker is broken"
    )
    assert len(sites) >= 8, f"suspiciously few side-effect sites detected: {len(sites)}"


def test_no_action_registry_launch_bypass() -> None:
    """G2 regression tripwire: no module should reference ACTION_INVOKE_REQUEST.

    ``ACTION_INVOKE_REQUEST`` reaches ``ActionRegistry.invoke``, which runs the
    frozen launch handlers with no ExecutionAuthority decision and no receipt.
    Workspace launches now go through WORKFLOW_EXECUTION_REQUEST instead.

    Scope limits — this is a name-level tripwire, not a proof:
      * it matches the *symbol*, so a module publishing the raw string
        ``"action.invoke.request"`` would slip past;
      * ``entity_bus_handlers.py`` is exempt because it *is* the subscriber that
        calls ``ActionRegistry.invoke``; this test does not constrain it.
    It catches the realistic regression — a new caller re-importing the symbol.
    """
    offenders: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        rel = path.relative_to(PACKAGE_ROOT).as_posix()
        if rel in {"core/events/topics.py", "core/entity/entity_bus_handlers.py"}:
            # Topic definition and the (subscriber-side) handler itself.
            continue
        text = path.read_text(encoding="utf-8")
        if "ACTION_INVOKE_REQUEST" in text:
            offenders.append(rel)
    assert not offenders, (
        "ACTION_INVOKE_REQUEST referenced outside its definition/handler — the "
        f"ActionRegistry launch bypass may be reopening: {offenders}"
    )
