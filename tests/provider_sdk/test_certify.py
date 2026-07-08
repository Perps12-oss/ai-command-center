"""Certification badge and CLI tests."""

from __future__ import annotations

import json
from io import StringIO
import sys

from ai_command_center.domain.orchestration_provider_manifest import OrchestrationProviderManifest
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.orchestration.providers.system_facts_provider import SystemFactsProvider
from ai_command_center.provider_sdk.adapters import OrchestrationProviderAdapter
from ai_command_center.provider_sdk.cli import main
from ai_command_center.provider_sdk.testing import (
    CERTIFICATION_BADGES,
    CertificationBadge,
    certify_orchestration_manifest,
    certify_runtime_manifest,
)


def test_six_certification_badges_exist() -> None:
    assert len(CERTIFICATION_BADGES) == 6
    names = {b.value for b in CertificationBadge}
    assert "receipt_safe" in names
    assert "permission_safe" in names


def test_certify_runtime_manifest_gold_passes_observable() -> None:
    manifest = RuntimeProviderManifest(
        id="native",
        name="Native",
        version="1.0",
        description="",
        entrypoint="builtin:native",
        capabilities=(CapabilityKind.CHAT,),
        permissions=("network.outbound",),
        events=("orchestration.run.snapshot", "orchestration.receipt"),
        health_probe="provider.health",
        certification_level="gold",
    )
    report = certify_runtime_manifest(
        manifest,
        OrchestrationProviderAdapter(SystemFactsProvider()),
    )
    observable = next(b for b in report.badges if b.badge == CertificationBadge.OBSERVABLE)
    assert observable.passed


def test_certify_orchestration_manifest() -> None:
    manifest = OrchestrationProviderManifest(
        id="system_facts",
        name="System Facts",
        version="1.0",
        description="",
        intents=("system_time_query",),
        permissions=("shell.execute",),
        events=("orchestration.receipt", "orchestration.run.snapshot"),
        health_probe="provider.health",
        certification_level="silver",
    )
    report = certify_orchestration_manifest(
        manifest,
        OrchestrationProviderAdapter(SystemFactsProvider()),
    )
    assert report.provider_id == "system_facts"
    assert len(report.badges) == 6


def test_cli_certify_system_facts() -> None:
    captured = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        code = main(["provider", "test", "system_facts", "--certify"])
    finally:
        sys.stdout = old_stdout
    payload = json.loads(captured.getvalue())
    assert payload["provider_id"] == "system_facts"
    assert "badges" in payload
    assert code in {0, 2}
