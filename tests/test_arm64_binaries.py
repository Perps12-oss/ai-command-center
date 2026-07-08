"""Risk area #1 - ARM64 vs x64 native-binary validation.

Validates the PE machine-type scanner (``scripts/check_arm64_binaries.py``):

* the PE parser correctly classifies crafted ARM64 / AMD64 / non-PE files, and
* :func:`scan` flags any non-ARM64 binary and exits non-zero.

The crafted-header tests run on every platform (no real binaries needed). A
final ``@pytest.mark.arm64`` test scans the *live* environment and asserts it is
100% ARM64 - it is skipped on x64 / emulated hosts where it would (correctly)
fail by design.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the script module directly (it lives under scripts/, not a package).
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_arm64_binaries.py"
_spec = importlib.util.spec_from_file_location("check_arm64_binaries", _SCRIPT)
assert _spec and _spec.loader
scanner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scanner)


def _make_pe(machine: int) -> bytes:
    """Build a minimal-but-valid PE image stub with the given machine word."""
    e_lfanew = 0x80
    buf = bytearray(0x100)
    buf[0:2] = b"MZ"
    buf[0x3C:0x40] = e_lfanew.to_bytes(4, "little")
    buf[e_lfanew : e_lfanew + 4] = b"PE\x00\x00"
    buf[e_lfanew + 4 : e_lfanew + 6] = machine.to_bytes(2, "little")
    return bytes(buf)


def test_reads_arm64_machine_type(tmp_path: Path) -> None:
    dll = tmp_path / "native_arm64.dll"
    dll.write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_ARM64))
    assert scanner.read_pe_machine(dll) == scanner.IMAGE_FILE_MACHINE_ARM64
    assert scanner.machine_name(scanner.read_pe_machine(dll)) == "ARM64"


def test_reads_amd64_machine_type(tmp_path: Path) -> None:
    dll = tmp_path / "emulated_x64.dll"
    dll.write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_AMD64))
    assert scanner.read_pe_machine(dll) == scanner.IMAGE_FILE_MACHINE_AMD64
    assert scanner.machine_name(scanner.read_pe_machine(dll)) == "AMD64"


def test_non_pe_file_is_ignored(tmp_path: Path) -> None:
    junk = tmp_path / "not_a_binary.dll"
    junk.write_bytes(b"this is plainly not a PE file")
    assert scanner.read_pe_machine(junk) is None


def test_scan_flags_x64_binaries_and_passes_arm64(tmp_path: Path) -> None:
    (tmp_path / "good.pyd").write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_ARM64))
    (tmp_path / "bad.dll").write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_AMD64))
    (tmp_path / "bad.exe").write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_I386))

    report = scanner.scan([tmp_path], allow=set())

    assert report["scanned"] == 3, f"expected 3 PE files scanned, got {report['scanned']}"
    offending = sorted(Path(o["path"]).name for o in report["offenders"])
    assert offending == ["bad.dll", "bad.exe"], (
        f"scanner must flag exactly the non-ARM64 binaries, got {offending}"
    )


def test_allowlist_exempts_named_binary(tmp_path: Path) -> None:
    (tmp_path / "legacy.dll").write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_AMD64))
    report = scanner.scan([tmp_path], allow={"legacy.dll"})
    assert report["offenders"] == [], "allowlisted binary should not be reported"


def test_cli_exits_nonzero_when_x64_present(tmp_path: Path) -> None:
    (tmp_path / "bad.dll").write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_AMD64))
    rc = scanner.main([str(tmp_path)])
    assert rc == 1, "CLI must exit non-zero when a non-ARM64 binary is found"


def test_cli_exits_zero_for_clean_tree(tmp_path: Path) -> None:
    (tmp_path / "ok.dll").write_bytes(_make_pe(scanner.IMAGE_FILE_MACHINE_ARM64))
    rc = scanner.main([str(tmp_path)])
    assert rc == 0, "CLI must exit zero when every binary is ARM64"


@pytest.mark.windows
@pytest.mark.arm64
@pytest.mark.skipif(
    sys.platform != "win32", reason="PE binaries only exist on Windows"
)
def test_live_environment_is_pure_arm64() -> None:
    """The active interpreter + site-packages must contain no x64 binaries.

    Skipped unless we are actually on native ARM64; on x64/emulated hosts this is
    expected to fail (that is the whole point of the gate).
    """
    import sys

    from ai_command_center.platform.detector import get_pe_machine_type, is_arm64

    if not is_arm64():
        pytest.skip("host is not native ARM64; live-environment gate is N/A here")
    if get_pe_machine_type(sys.executable) != "ARM64":
        pytest.skip(
            "Python interpreter is not native ARM64 PE "
            "(x64/emulated runtime on ARM64 host); live-environment gate is N/A here"
        )

    report = scanner.scan(scanner.default_scan_roots(), allow=set())
    assert not report["offenders"], (
        "non-ARM64 binaries present in a native ARM64 environment:\n"
        + "\n".join(f"  {o['machine']}: {o['path']}" for o in report["offenders"])
    )
