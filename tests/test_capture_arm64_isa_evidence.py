"""ISA evidence capture: records candidates as pending; never grants Allow."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capture_arm64_isa_evidence.py"
_spec = importlib.util.spec_from_file_location("capture_arm64_isa_evidence", _SCRIPT)
assert _spec and _spec.loader
capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(capture)


def test_allowlist_candidates_are_pending_never_allow() -> None:
    rows = capture.collect_allowlist_candidates()
    ids = {r["row_id"] for r in rows}
    assert ids == {"aiohttp_transitives", "watchdog", "pywin32"}
    for row in rows:
        assert row["policy"] == "pending"
        assert row["inference_critical"] is False
        assert row["runtime_impact"] == "unestablished"


def test_collect_payload_release_environment_claim_matches_host(tmp_path: Path) -> None:
    payload = capture.collect_payload(include_scanner=True)
    assert payload["schema"] == "acc.arm64_isa_evidence.v1"
    python = payload["python"]
    native_release = (
        payload["host"]["sys_platform"] == "win32"
        and python["is_arm64_fn"] is True
        and python["pe_machine"] == "ARM64"
    )
    expected_claim = (
        "valid_only_on_windows_arm64_native_python"
        if native_release
        else "not_a_native_arm64_release_environment"
    )
    assert payload["release_environment_claim"] == expected_claim
    assert "WARN is not a grant" in payload["policy_note"]
    out = tmp_path / "isa_evidence.json"
    rc = capture.main(["--out", str(out), "--skip-preflight", "--skip-scanner"])
    assert rc == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["preflight"]["ran"] is False
    assert all(r["policy"] == "pending" for r in saved["allowlist_candidates"])
