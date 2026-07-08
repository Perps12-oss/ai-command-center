"""Per-capability runtime provider settings (ARI Phase 4 + Phase 5 discovery)."""

from __future__ import annotations

from ai_command_center.domain.runtime_capability import CapabilityKind

BASE_CAPABILITY_PROVIDER_CHOICES: tuple[str, ...] = ("native", "qwenpaw", "auto")

# Backward-compatible alias for static consumers.
CAPABILITY_PROVIDER_CHOICES: tuple[str, ...] = BASE_CAPABILITY_PROVIDER_CHOICES

_discovered_provider_ids: list[str] = []


def register_discovered_providers(provider_ids: list[str]) -> None:
    """Register plugin provider ids discovered at runtime (deduped, stable order)."""
    global _discovered_provider_ids
    seen = set(BASE_CAPABILITY_PROVIDER_CHOICES)
    merged: list[str] = []
    for provider_id in provider_ids:
        normalized = str(provider_id).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    _discovered_provider_ids = merged


def get_capability_provider_choices() -> tuple[str, ...]:
    """Return static choices plus discovered runtime plugin provider ids."""
    if not _discovered_provider_ids:
        return BASE_CAPABILITY_PROVIDER_CHOICES
    return BASE_CAPABILITY_PROVIDER_CHOICES + tuple(_discovered_provider_ids)


def capability_provider_label(provider_id: str) -> str:
    """Human-readable label for a provider id in settings UI."""
    labels = {
        "native": "Native",
        "qwenpaw": "QwenPaw",
        "auto": "Auto",
        "stub_echo": "Stub Echo",
    }
    return labels.get(provider_id, provider_id.replace("_", " ").title())


DEFAULT_CAPABILITY_PROVIDER_MAP: dict[str, str] = {
    CapabilityKind.CHAT.value: "native",
    CapabilityKind.PLANNING.value: "qwenpaw",
    CapabilityKind.CODING.value: "qwenpaw",
    CapabilityKind.RESEARCH.value: "native",
    CapabilityKind.AUTOMATION.value: "native",
    CapabilityKind.AGENTS.value: "native",
    CapabilityKind.MEMORY.value: "native",
}

CAPABILITY_KIND_LABELS: dict[str, str] = {
    CapabilityKind.CHAT.value: "Chat",
    CapabilityKind.PLANNING.value: "Planning",
    CapabilityKind.CODING.value: "Coding",
    CapabilityKind.RESEARCH.value: "Research",
    CapabilityKind.AUTOMATION.value: "Automation",
    CapabilityKind.AGENTS.value: "Agents",
    CapabilityKind.MEMORY.value: "Memory",
}


def settings_key_for_kind(kind: str) -> str:
    return f"capability_provider_{kind}"


def capability_provider_map_from_payload(payload: dict[str, object]) -> dict[str, str]:
    """Build kind → provider choice map from persisted settings payload."""
    choices = get_capability_provider_choices()
    result: dict[str, str] = {}
    for kind in DEFAULT_CAPABILITY_PROVIDER_MAP:
        raw = str(payload.get(settings_key_for_kind(kind), "auto")).strip().lower() or "auto"
        if raw not in choices:
            raw = DEFAULT_CAPABILITY_PROVIDER_MAP[kind]
        result[kind] = raw
    return result


def resolve_capability_provider(
    kind: CapabilityKind | str,
    user_map: dict[str, str] | None = None,
) -> str:
    """Resolve effective provider id for a capability kind."""
    kind_key = kind.value if isinstance(kind, CapabilityKind) else str(kind)
    choice = (user_map or {}).get(kind_key, "auto")
    if choice == "auto":
        return DEFAULT_CAPABILITY_PROVIDER_MAP.get(kind_key, "native")
    return choice
