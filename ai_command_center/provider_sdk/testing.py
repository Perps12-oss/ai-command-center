"""Provider certification badges and harness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_command_center.domain.orchestration_provider_manifest import OrchestrationProviderManifest
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.provider_sdk.adapters import CertifiableProvider
from ai_command_center.provider_sdk.base import ProviderTestContext
from ai_command_center.provider_sdk.receipts import receipt_is_complete


class CertificationBadge(str, Enum):
    RECEIPT_SAFE = "receipt_safe"
    TRUTH_SAFE = "truth_safe"
    OBSERVABLE = "observable"
    REPLAY_SAFE = "replay_safe"
    DETERMINISTIC = "deterministic"
    PERMISSION_SAFE = "permission_safe"


CERTIFICATION_BADGES: tuple[CertificationBadge, ...] = tuple(CertificationBadge)


@dataclass(frozen=True, slots=True)
class BadgeResult:
    badge: CertificationBadge
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CertificationReport:
    provider_id: str
    badges: tuple[BadgeResult, ...]

    @property
    def passed(self) -> bool:
        return all(b.passed for b in self.badges)

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "passed": self.passed,
            "badges": [
                {"badge": b.badge.value, "passed": b.passed, "detail": b.detail}
                for b in self.badges
            ],
        }


def _check_receipt_safe(manifest_events: tuple[str, ...]) -> BadgeResult:
    observable = any("receipt" in e or "orchestration" in e for e in manifest_events)
    sample = {
        "receipt_id": "r1",
        "request_id": "req1",
        "intent": "test",
        "provider_id": "test",
        "success": True,
    }
    return BadgeResult(
        CertificationBadge.RECEIPT_SAFE,
        receipt_is_complete(sample) and (observable or bool(manifest_events)),
        "receipt contract + event surface",
    )


def _check_truth_safe(certification_level: str) -> BadgeResult:
    passed = certification_level in {"silver", "gold"}
    return BadgeResult(
        CertificationBadge.TRUTH_SAFE,
        passed,
        "requires silver or gold certification_level",
    )


def _check_observable(events: tuple[str, ...], health_probe: str) -> BadgeResult:
    passed = bool(events) and bool(health_probe)
    return BadgeResult(
        CertificationBadge.OBSERVABLE,
        passed,
        "events and health_probe declared",
    )


def _check_replay_safe(events: tuple[str, ...]) -> BadgeResult:
    passed = any(
        token in e
        for e in events
        for token in ("run.snapshot", "orchestration.run", "chat.complete")
    )
    return BadgeResult(
        CertificationBadge.REPLAY_SAFE,
        passed,
        "replayable bus events declared",
    )


def _check_deterministic(provider: CertifiableProvider) -> BadgeResult:
    try:
        first = provider.health()
        second = provider.health()
        passed = first == second
        detail = "health probe is stable"
    except Exception as exc:  # noqa: BLE001 — certification boundary
        passed = False
        detail = str(exc)
    return BadgeResult(CertificationBadge.DETERMINISTIC, passed, detail)


def _check_permission_safe(permissions: tuple[str, ...]) -> BadgeResult:
    passed = bool(permissions)
    return BadgeResult(
        CertificationBadge.PERMISSION_SAFE,
        passed,
        "permissions explicitly declared",
    )


def certify_runtime_manifest(
    manifest: RuntimeProviderManifest,
    provider: CertifiableProvider | None = None,
    *,
    ctx: ProviderTestContext | None = None,
) -> CertificationReport:
    ctx = ctx or ProviderTestContext(provider_id=manifest.id)
    badges = [
        _check_receipt_safe(manifest.events),
        _check_truth_safe(manifest.certification_level),
        _check_observable(manifest.events, manifest.health_probe),
        _check_replay_safe(manifest.events),
        _check_permission_safe(manifest.permissions),
    ]
    if provider is not None:
        badges.append(_check_deterministic(provider))
    else:
        badges.append(
            BadgeResult(
                CertificationBadge.DETERMINISTIC,
                False,
                "no live provider instance",
            )
        )
    return CertificationReport(provider_id=ctx.provider_id, badges=tuple(badges))


def certify_orchestration_manifest(
    manifest: OrchestrationProviderManifest,
    provider: CertifiableProvider | None = None,
    *,
    ctx: ProviderTestContext | None = None,
) -> CertificationReport:
    ctx = ctx or ProviderTestContext(provider_id=manifest.id)
    badges = [
        _check_receipt_safe(manifest.events),
        _check_truth_safe(manifest.certification_level),
        _check_observable(manifest.events, manifest.health_probe),
        _check_replay_safe(manifest.events),
        _check_permission_safe(manifest.permissions),
    ]
    if provider is not None:
        badges.append(_check_deterministic(provider))
    else:
        badges.append(
            BadgeResult(
                CertificationBadge.DETERMINISTIC,
                False,
                "no live provider instance",
            )
        )
    return CertificationReport(provider_id=ctx.provider_id, badges=tuple(badges))


def certify_provider(
    provider_id: str,
    *,
    runtime_manifest: RuntimeProviderManifest | None = None,
    orchestration_manifest: OrchestrationProviderManifest | None = None,
    provider: CertifiableProvider | None = None,
    dev_mode: bool = False,
) -> CertificationReport:
    ctx = ProviderTestContext(provider_id=provider_id, dev_mode=dev_mode)
    if runtime_manifest is not None:
        return certify_runtime_manifest(runtime_manifest, provider, ctx=ctx)
    if orchestration_manifest is not None:
        return certify_orchestration_manifest(orchestration_manifest, provider, ctx=ctx)
    return CertificationReport(
        provider_id=provider_id,
        badges=(
            BadgeResult(b, False, "manifest not found") for b in CERTIFICATION_BADGES
        ),
    )
