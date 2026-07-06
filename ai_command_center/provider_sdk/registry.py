"""Manifest validation and registry with certification minimums."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from ai_command_center.domain.orchestration_provider_manifest import OrchestrationProviderManifest
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.provider_sdk.base import SDK_VERSION
from ai_command_center.provider_sdk.permissions import KNOWN_PERMISSIONS

_logger = logging.getLogger(__name__)

_CERTIFICATION_LEVELS = frozenset({"bronze", "silver", "gold"})
_MIN_SDK_FOR_CERTIFICATION = "1.0"


@dataclass(frozen=True, slots=True)
class ManifestValidationResult:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


def _coerce_str_tuple(value: object) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),) if str(value).strip() else ()


def _check_certification_minimums(
    *,
    provider_id: str,
    permissions: tuple[str, ...],
    events: tuple[str, ...],
    health_probe: str,
    certification_level: str,
    min_sdk_version: str,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not certification_level:
        warnings.append(f"{provider_id}: certification_level not declared")
    elif certification_level not in _CERTIFICATION_LEVELS:
        errors.append(f"{provider_id}: invalid certification_level {certification_level!r}")

    if not permissions:
        warnings.append(f"{provider_id}: no permissions declared")
    else:
        unknown = [p for p in permissions if p not in KNOWN_PERMISSIONS]
        for perm in unknown:
            warnings.append(f"{provider_id}: unknown permission {perm!r}")

    if not events:
        warnings.append(f"{provider_id}: no events declared (observability gap)")

    if not health_probe:
        warnings.append(f"{provider_id}: health_probe not declared")

    if min_sdk_version and min_sdk_version > SDK_VERSION:
        errors.append(
            f"{provider_id}: requires SDK {min_sdk_version}, runtime has {SDK_VERSION}"
        )

    return errors, warnings


def validate_runtime_manifest(manifest: RuntimeProviderManifest) -> ManifestValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not manifest.id:
        errors.append("manifest id is required")
    if not manifest.entrypoint:
        errors.append(f"{manifest.id or '?'}: entrypoint is required")
    if not manifest.capabilities:
        errors.append(f"{manifest.id}: at least one capability is required")

    cert_errors, cert_warnings = _check_certification_minimums(
        provider_id=manifest.id or "?",
        permissions=manifest.permissions,
        events=manifest.events,
        health_probe=manifest.health_probe,
        certification_level=manifest.certification_level,
        min_sdk_version=manifest.min_sdk_version,
    )
    errors.extend(cert_errors)
    warnings.extend(cert_warnings)

    return ManifestValidationResult(
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def validate_orchestration_manifest(
    manifest: OrchestrationProviderManifest,
) -> ManifestValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not manifest.id:
        errors.append("manifest id is required")
    if not manifest.intents:
        errors.append(f"{manifest.id or '?'}: at least one intent is required")

    cert_errors, cert_warnings = _check_certification_minimums(
        provider_id=manifest.id or "?",
        permissions=manifest.permissions,
        events=manifest.events,
        health_probe=manifest.health_probe,
        certification_level=manifest.certification_level,
        min_sdk_version=manifest.min_sdk_version,
    )
    errors.extend(cert_errors)
    warnings.extend(cert_warnings)

    return ManifestValidationResult(
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _dev_mode() -> bool:
    return os.environ.get("ACC_DEV_MODE", "").lower() in {"1", "true", "yes"}


@dataclass
class ProviderManifestRegistry:
    """Loads manifests and emits dev-mode certification warnings."""

    runtime_manifests: list[RuntimeProviderManifest] = field(default_factory=list)
    orchestration_manifests: list[OrchestrationProviderManifest] = field(
        default_factory=list
    )

    def register_runtime(self, manifest: RuntimeProviderManifest) -> ManifestValidationResult:
        result = validate_runtime_manifest(manifest)
        if result.ok:
            self.runtime_manifests.append(manifest)
        self._emit_warnings(manifest.id, result)
        return result

    def register_orchestration(
        self, manifest: OrchestrationProviderManifest
    ) -> ManifestValidationResult:
        result = validate_orchestration_manifest(manifest)
        if result.ok:
            self.orchestration_manifests.append(manifest)
        self._emit_warnings(manifest.id, result)
        return result

    @staticmethod
    def _emit_warnings(provider_id: str, result: ManifestValidationResult) -> None:
        for error in result.errors:
            _logger.error("manifest %s: %s", provider_id, error)
        if not _dev_mode():
            return
        for warning in result.warnings:
            _logger.warning("manifest %s: %s", provider_id, warning)
