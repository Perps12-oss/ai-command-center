"""ACC provider certification CLI — ``python -m ai_command_center.provider_sdk.cli``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from ai_command_center.domain.orchestration_provider_manifest import OrchestrationProviderManifest
from ai_command_center.domain.runtime_capability import CapabilityKind
from ai_command_center.domain.runtime_provider_manifest import RuntimeProviderManifest
from ai_command_center.orchestration.providers.provider_registry import OrchestrationProviderRegistry
from ai_command_center.provider_sdk.adapters import OrchestrationProviderAdapter, as_certifiable
from ai_command_center.provider_sdk.registry import ProviderManifestRegistry
from ai_command_center.provider_sdk.testing import certify_provider
from ai_command_center.runtime.provider_registry import build_default_runtime_registry

_RUNTIME_MANIFESTS = (
    Path(__file__).resolve().parents[2] / "plugins" / "runtime_manifests"
)
_ORCH_MANIFESTS = (
    Path(__file__).resolve().parents[2] / "plugins" / "orchestration_manifests"
)


def _parse_runtime(data: dict) -> RuntimeProviderManifest | None:
    provider_id = str(data.get("id", "")).strip()
    if not provider_id:
        return None
    caps = []
    for item in data.get("capabilities") or []:
        try:
            caps.append(CapabilityKind(str(item).strip().lower()))
        except ValueError:
            continue
    if not caps:
        return None
    return RuntimeProviderManifest(
        id=provider_id,
        name=str(data.get("name", provider_id)),
        version=str(data.get("version", "1.0")),
        description=str(data.get("description", "")),
        entrypoint=str(data.get("entrypoint", "")),
        capabilities=tuple(caps),
        enabled=bool(data.get("enabled", True)),
        kind=str(data.get("kind", "runtime_provider")),
        permissions=tuple(str(p) for p in (data.get("permissions") or [])),
        events=tuple(str(e) for e in (data.get("events") or [])),
        health_probe=str(data.get("health_probe", "")),
        dependencies=tuple(str(d) for d in (data.get("dependencies") or [])),
        certification_level=str(data.get("certification_level", "")),
        min_sdk_version=str(data.get("min_sdk_version", "1.0")),
    )


def _parse_orchestration(data: dict) -> OrchestrationProviderManifest | None:
    provider_id = str(data.get("id", "")).strip()
    if not provider_id:
        return None
    intents = tuple(str(i) for i in (data.get("intents") or []))
    if not intents:
        return None
    return OrchestrationProviderManifest(
        id=provider_id,
        name=str(data.get("name", provider_id)),
        version=str(data.get("version", "1.0")),
        description=str(data.get("description", "")),
        intents=intents,
        permissions=tuple(str(p) for p in (data.get("permissions") or [])),
        events=tuple(str(e) for e in (data.get("events") or [])),
        health_probe=str(data.get("health_probe", "")),
        dependencies=tuple(str(d) for d in (data.get("dependencies") or [])),
        certification_level=str(data.get("certification_level", "")),
        min_sdk_version=str(data.get("min_sdk_version", "1.0")),
        enabled=bool(data.get("enabled", True)),
        kind=str(data.get("kind", "orchestration_provider")),
        entrypoint=str(data.get("entrypoint", "")),
    )


def _load_manifest(provider_id: str) -> tuple[RuntimeProviderManifest | None, OrchestrationProviderManifest | None]:
    runtime: RuntimeProviderManifest | None = None
    orchestration: OrchestrationProviderManifest | None = None
    if _RUNTIME_MANIFESTS.is_dir():
        for path in _RUNTIME_MANIFESTS.glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if str(data.get("id", "")).strip() == provider_id:
                runtime = _parse_runtime(data)
                break
    if _ORCH_MANIFESTS.is_dir():
        for path in _ORCH_MANIFESTS.glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if str(data.get("id", "")).strip() == provider_id:
                orchestration = _parse_orchestration(data)
                break
    return runtime, orchestration


def _resolve_live_provider(provider_id: str) -> object | None:
    orch = OrchestrationProviderRegistry().get(provider_id)
    if orch is not None:
        return OrchestrationProviderAdapter(orch)
    runtime = build_default_runtime_registry().get(provider_id)
    if runtime is not None:
        from ai_command_center.provider_sdk.adapters import RuntimeProviderAdapter

        return RuntimeProviderAdapter(runtime)
    return None


def cmd_provider_test(args: argparse.Namespace) -> int:
    provider_id = args.provider_id.strip()
    runtime_manifest, orch_manifest = _load_manifest(provider_id)
    if runtime_manifest is None and orch_manifest is None:
        print(f"provider not found: {provider_id}", file=sys.stderr)
        return 1

    registry = ProviderManifestRegistry()
    if runtime_manifest is not None:
        result = registry.register_runtime(runtime_manifest)
        if not args.certify:
            print(f"validate runtime {provider_id}: ok={result.ok}")
            for w in result.warnings:
                print(f"  warn: {w}")
            for e in result.errors:
                print(f"  error: {e}")
        if not result.ok:
            return 1
    if orch_manifest is not None:
        result = registry.register_orchestration(orch_manifest)
        if not args.certify:
            print(f"validate orchestration {provider_id}: ok={result.ok}")
            for w in result.warnings:
                print(f"  warn: {w}")
            for e in result.errors:
                print(f"  error: {e}")
        if not result.ok:
            return 1

    live = _resolve_live_provider(provider_id)
    certifiable = as_certifiable(live) if live is not None else None

    if args.certify:
        report = certify_provider(
            provider_id,
            runtime_manifest=runtime_manifest,
            orchestration_manifest=orch_manifest,
            provider=certifiable,
            dev_mode=True,
        )
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.passed else 2

    if certifiable is not None:
        healthy, detail = certifiable.health()
        print(f"health: {'ok' if healthy else 'fail'} — {detail}")
    else:
        print("health: skipped (no live provider)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acc")
    sub = parser.add_subparsers(dest="command", required=True)
    provider = sub.add_parser("provider")
    provider_sub = provider.add_subparsers(dest="provider_command", required=True)
    test = provider_sub.add_parser("test")
    test.add_argument("provider_id")
    test.add_argument("--certify", action="store_true", help="run certification badges")
    test.set_defaults(func=cmd_provider_test)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
