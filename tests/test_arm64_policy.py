"""Two-tier ARM64 policy: allowlist vs FAIL."""

from ai_command_center.platform.arm64_policy import (
    is_allowlisted_emulation_path,
    wheel_severity,
)


def test_wheel_severity_allowlist_pass() -> None:
    assert (
        wheel_severity("emulated_amd64", "aiohttp", critical=False, perf_critical=False)
        == "PASS"
    )
    assert (
        wheel_severity("emulated_amd64", "psutil", critical=True, perf_critical=False)
        == "PASS"
    )


def test_wheel_severity_unknown_emulated_fails() -> None:
    assert (
        wheel_severity("emulated_amd64", "mystery-pkg", critical=False, perf_critical=False)
        == "FAIL"
    )


def test_path_tokens_map_allowlisted_packages(tmp_path) -> None:
    assert is_allowlisted_emulation_path(tmp_path / "site-packages" / "yarl" / "x.pyd")
    assert is_allowlisted_emulation_path(tmp_path / "PIL" / "_imaging.pyd")
    assert not is_allowlisted_emulation_path(tmp_path / "mystery" / "x.pyd")
