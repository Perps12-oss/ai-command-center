"""Intention validation before TOOL_INVOKE (ADR-018).

Parse failure = malformed intention payload shape.
Validation failure = well-shaped intention that violates catalog / business rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ai_command_center.domain.intention import Intention


# Built-in required arg keys when catalog parameters are absent.
_BUILTIN_REQUIRED_ARGS: dict[str, frozenset[str]] = {
    "shell": frozenset({"command"}),
    "launch_application": frozenset({"application"}),
}

_EXTERNAL_PREFIXES = ("mcp.", "external.", "mcp:")
_LLM_CAPABILITIES = frozenset({"llm", "chat"})


@dataclass(frozen=True, slots=True)
class IntentionValidationResult:
    ok: bool
    kind: str = ""  # "" | "parse" | "validation"
    message: str = ""
    intention: Intention | None = None


def _is_external(capability: str) -> bool:
    lowered = capability.lower()
    return any(lowered.startswith(p) for p in _EXTERNAL_PREFIXES)


def _is_llm(capability: str) -> bool:
    return capability.strip().lower() in _LLM_CAPABILITIES


def _is_agent(capability: str) -> bool:
    return capability.strip().lower().startswith("agent.")


def parse_intention_payload(payload: Mapping[str, Any] | None) -> IntentionValidationResult:
    """Parse raw payload into Intention. Failures are *parse* class."""
    if not isinstance(payload, Mapping):
        return IntentionValidationResult(
            ok=False, kind="parse", message="intention payload must be a mapping"
        )
    try:
        capability = payload.get("capability")
        if capability is None and "tool" in payload:
            # Reject executable-tool shape as primary contract (ADR-018).
            return IntentionValidationResult(
                ok=False,
                kind="parse",
                message="executable tool payload rejected; use capability intention",
            )
        if not isinstance(capability, str):
            return IntentionValidationResult(
                ok=False, kind="parse", message="capability must be a string"
            )
        raw_args = payload.get("args", {})
        if raw_args is None:
            raw_args = {}
        if not isinstance(raw_args, dict):
            return IntentionValidationResult(
                ok=False, kind="parse", message="args must be a dict"
            )
        intention = Intention(
            capability=capability.strip(),
            args=dict(raw_args),
            require_approval=bool(payload.get("require_approval", False)),
            step_id=str(payload.get("step_id", "")),
        )
    except (TypeError, ValueError) as exc:
        return IntentionValidationResult(
            ok=False, kind="parse", message=f"malformed intention: {exc}"
        )
    return IntentionValidationResult(ok=True, intention=intention)


def validate_intention(
    intention: Intention,
    *,
    known_capabilities: set[str] | frozenset[str] | None = None,
    catalog_parameters: Mapping[str, Mapping[str, Any]] | None = None,
) -> IntentionValidationResult:
    """Validate business/catalog rules. Failures are *validation* class."""
    if not intention.capability:
        return IntentionValidationResult(
            ok=False,
            kind="validation",
            message="capability is required",
            intention=intention,
        )

    cap = intention.capability
    known = known_capabilities
    if known is not None and not _is_external(cap) and not _is_llm(cap) and not _is_agent(cap):
        if cap not in known:
            return IntentionValidationResult(
                ok=False,
                kind="validation",
                message=f"capability {cap!r} is not in the capability catalog",
                intention=intention,
            )

    params = None
    if catalog_parameters and cap in catalog_parameters:
        params = catalog_parameters[cap]
    required: set[str] = set()
    if isinstance(params, Mapping):
        # Support {"required": [...]} or flat {name: {required: true}}
        if "required" in params and isinstance(params["required"], (list, tuple)):
            required.update(str(x) for x in params["required"])
        else:
            for name, meta in params.items():
                if isinstance(meta, Mapping) and meta.get("required"):
                    required.add(str(name))
    elif cap in _BUILTIN_REQUIRED_ARGS:
        required.update(_BUILTIN_REQUIRED_ARGS[cap])

    missing = sorted(k for k in required if k not in intention.args)
    if missing:
        return IntentionValidationResult(
            ok=False,
            kind="validation",
            message=f"missing required args: {', '.join(missing)}",
            intention=intention,
        )

    return IntentionValidationResult(ok=True, intention=intention)


def validate_intention_payload(
    payload: Mapping[str, Any] | None,
    *,
    known_capabilities: set[str] | frozenset[str] | None = None,
    catalog_parameters: Mapping[str, Mapping[str, Any]] | None = None,
) -> IntentionValidationResult:
    parsed = parse_intention_payload(payload)
    if not parsed.ok or parsed.intention is None:
        return parsed
    return validate_intention(
        parsed.intention,
        known_capabilities=known_capabilities,
        catalog_parameters=catalog_parameters,
    )


__all__ = [
    "IntentionValidationResult",
    "parse_intention_payload",
    "validate_intention",
    "validate_intention_payload",
]
