"""UCGS CI/local diff semantics — proves the gate is not inert.

P1-A regression: CI must audit ``base...HEAD`` (range), not an empty staged index.
Local pre-commit continues to use staged (``git diff --cached``).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / "tools"


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _init_ucgs_repo(tmp_path: Path) -> Path:
    """Minimal git repo with UCGS config + ACC profile (copied from project)."""
    root = tmp_path / "ucgs_proj"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "ucgs-test@example.com")
    _git(root, "config", "user.name", "UCGS Test")

    shutil.copy(REPO_ROOT / "ucgs.config.yaml", root / "ucgs.config.yaml")
    profiles = root / "ucgs.profiles"
    profiles.mkdir()
    shutil.copy(
        REPO_ROOT / "ucgs.profiles" / "ai-command-center.yaml",
        profiles / "ai-command-center.yaml",
    )

    # Baseline tree — no violations.
    (root / "ai_command_center").mkdir()
    (root / "ai_command_center" / "ui").mkdir(parents=True)
    (root / "ai_command_center" / "ui" / "safe.py").write_text(
        "\"\"\"UI module without forbidden imports.\"\"\"\n\ndef render() -> None:\n    return None\n",
        encoding="utf-8",
    )
    (root / "ai_command_center" / "core").mkdir()
    (root / "ai_command_center" / "core" / "contracts.py").write_text(
        textwrap.dedent(
            """\
            CONTEXT_BUNDLE_VERSION = "1.0"
            OLLAMA_SERVICE_API_VERSION = "1.0"
            SUPPORTED_VERSIONS = ("1.0",)
            """
        ),
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "baseline")
    return root


def _run_ucgs(root: Path, *, write_local: bool = False) -> dict:
    import sys

    sys.path.insert(0, str(TOOLS))
    from ucgs_runner import run_ucgs

    return run_ucgs(root, write_local=write_local)


def _gate(report: dict, *, enforcement: str = "block") -> int:
    import sys
    import tempfile

    sys.path.insert(0, str(TOOLS))
    from ucgs_ci_gate import main as gate_main

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        yaml.dump(report, handle)
        path = handle.name
    old = os.environ.get("UCGS_ENFORCEMENT")
    os.environ["UCGS_ENFORCEMENT"] = enforcement
    try:
        return int(gate_main(path))
    finally:
        if old is None:
            os.environ.pop("UCGS_ENFORCEMENT", None)
        else:
            os.environ["UCGS_ENFORCEMENT"] = old
        Path(path).unlink(missing_ok=True)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("UCGS_DIFF_MODE", "UCGS_DIFF_BASE", "UCGS_DIFF_HEAD", "UCGS_ENFORCEMENT"):
        monkeypatch.delenv(key, raising=False)


def test_ci_range_mode_not_empty_when_staged_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Clean checkout (empty staged) must still see PR commits under range mode."""
    root = _init_ucgs_repo(tmp_path)
    base = _git(root, "rev-parse", "HEAD")

    evil = root / "ai_command_center" / "ui" / "evil.py"
    evil.write_text(
        "from ai_command_center.services.ollama_service import OllamaService\n",
        encoding="utf-8",
    )
    _git(root, "add", "ai_command_center/ui/evil.py")
    _git(root, "commit", "-m", "add ui service import")
    head = _git(root, "rev-parse", "HEAD")

    # Simulate CI: nothing staged.
    assert _git(root, "diff", "--cached", "--name-only") == ""

    monkeypatch.setenv("UCGS_DIFF_MODE", "range")
    monkeypatch.setenv("UCGS_DIFF_BASE", base)
    monkeypatch.setenv("UCGS_DIFF_HEAD", head)

    report = _run_ucgs(root)
    assert report["context"]["diff_mode"] == "range"
    assert "ai_command_center/ui/evil.py" in report["context"]["changed_files"]
    assert report["ucgs_summary"]["verdict"] == "FAIL"
    assert report["ucgs_summary"]["risk_level"] in {"S4", "S5"}
    assert any("OllamaService" in v["message"] for v in report["violations"])
    assert _gate(report, enforcement="block") == 1


def test_ci_compliant_range_diff_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    root = _init_ucgs_repo(tmp_path)
    base = _git(root, "rev-parse", "HEAD")
    safe = root / "ai_command_center" / "ui" / "more_safe.py"
    safe.write_text("def paint() -> str:\n    return 'ok'\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "safe ui change")
    head = _git(root, "rev-parse", "HEAD")

    monkeypatch.setenv("UCGS_DIFF_MODE", "range")
    monkeypatch.setenv("UCGS_DIFF_BASE", base)
    monkeypatch.setenv("UCGS_DIFF_HEAD", head)

    report = _run_ucgs(root)
    assert report["context"]["diff_mode"] == "range"
    assert report["ucgs_summary"]["verdict"] == "PASS"
    assert _gate(report, enforcement="block") == 0


def test_local_staged_mode_still_detects_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    root = _init_ucgs_repo(tmp_path)
    evil = root / "ai_command_center" / "ui" / "staged_evil.py"
    evil.write_text(
        "from ai_command_center.db.repository import Repository\n",
        encoding="utf-8",
    )
    _git(root, "add", "ai_command_center/ui/staged_evil.py")
    # Staged but not committed — local pre-commit path.
    monkeypatch.setenv("UCGS_DIFF_MODE", "staged")

    report = _run_ucgs(root)
    assert report["context"]["diff_mode"] == "staged"
    assert "ai_command_center/ui/staged_evil.py" in report["context"]["changed_files"]
    assert report["ucgs_summary"]["verdict"] == "FAIL"
    assert _gate(report, enforcement="block") == 1


def test_staged_mode_empty_index_passes_without_looking_at_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Local staged mode with empty index is intentional (nothing to commit)."""
    root = _init_ucgs_repo(tmp_path)
    base = _git(root, "rev-parse", "HEAD")
    evil = root / "ai_command_center" / "ui" / "committed_evil.py"
    evil.write_text(
        "from ai_command_center.services.ollama_service import OllamaService\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "evil already committed")
    assert _git(root, "diff", "--cached", "--name-only") == ""

    monkeypatch.setenv("UCGS_DIFF_MODE", "staged")
    report = _run_ucgs(root)
    assert report["context"]["changed_files"] == []
    assert report["ucgs_summary"]["verdict"] == "PASS"

    # Same tree under range mode must FAIL.
    monkeypatch.setenv("UCGS_DIFF_MODE", "range")
    monkeypatch.setenv("UCGS_DIFF_BASE", base)
    monkeypatch.setenv("UCGS_DIFF_HEAD", "HEAD")
    report_ci = _run_ucgs(root)
    assert report_ci["ucgs_summary"]["verdict"] == "FAIL"


def test_range_mode_without_base_fail_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    root = _init_ucgs_repo(tmp_path)
    monkeypatch.setenv("UCGS_DIFF_MODE", "range")
    # Deliberately omit UCGS_DIFF_BASE.
    report = _run_ucgs(root)
    assert report["ucgs_summary"]["verdict"] == "FAIL"
    assert report["ucgs_summary"]["risk_level"] in {"S4", "S5"}
    assert any(v["rule_id"] == "ucgs_diff_range_unresolved" for v in report["violations"])
    assert _gate(report, enforcement="block") == 1


def test_all_four_checks_receive_range_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    root = _init_ucgs_repo(tmp_path)
    base = _git(root, "rev-parse", "HEAD")
    # Touch many files + a secret-like line to exercise multiple checks.
    for i in range(22):
        (root / f"file_{i}.txt").write_text(f"x{i}\n", encoding="utf-8")
    evil = root / "ai_command_center" / "ui" / "leak.py"
    evil.write_text(
        'api_key = "sk-live-not-real-but-forbidden"\n'
        "from ai_command_center.services.ollama_service import OllamaService\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "multi-check violation")
    head = _git(root, "rev-parse", "HEAD")

    monkeypatch.setenv("UCGS_DIFF_MODE", "range")
    monkeypatch.setenv("UCGS_DIFF_BASE", base)
    monkeypatch.setenv("UCGS_DIFF_HEAD", head)

    report = _run_ucgs(root)
    assert report["context"]["checks_run"] == [
        "layer_imports",
        "forbidden_patterns",
        "large_commit",
        "contract_drift",
    ]
    assert report["context"]["changed_files"]
    # layer and/or secrets should violate; large_commit may warn.
    assert report["ucgs_summary"]["verdict"] in {"FAIL", "WARN"}
    assert report["violations"] or report["warnings"]


def test_block_enforcement_rejects_fail_allows_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    root = _init_ucgs_repo(tmp_path)
    base = _git(root, "rev-parse", "HEAD")
    monkeypatch.setenv("UCGS_DIFF_MODE", "range")
    monkeypatch.setenv("UCGS_DIFF_BASE", base)
    monkeypatch.setenv("UCGS_DIFF_HEAD", "HEAD")
    ok = _run_ucgs(root)
    assert _gate(ok, enforcement="block") == 0

    evil = root / "ai_command_center" / "ui" / "bad.py"
    evil.write_text(
        "from ai_command_center.services.ollama_service import OllamaService\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "bad")
    monkeypatch.setenv("UCGS_DIFF_HEAD", _git(root, "rev-parse", "HEAD"))
    bad = _run_ucgs(root)
    assert bad["ucgs_summary"]["verdict"] == "FAIL"
    assert _gate(bad, enforcement="block") == 1
    # warn mode must not block
    assert _gate(bad, enforcement="warn") == 0
