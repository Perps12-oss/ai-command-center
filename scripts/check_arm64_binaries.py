#!/usr/bin/env python3
"""Fail-by-default scan for non-ARM64 native binaries in the Python environment.

Risk area #1 - Platform-specific blind spots (ARM64 vs x64).

Walks the active Python environment (interpreter prefix + every ``site-packages``
directory, or paths passed on the command line) and inspects the PE *machine
type* of every ``.exe``, ``.dll`` and ``.pyd``. Any binary that is not
``IMAGE_FILE_MACHINE_ARM64`` (``0xAA64``) is reported and the script exits with a
non-zero status so a pre-commit hook / CI job blocks the commit.

Usage
-----
    python scripts/check_arm64_binaries.py                # scan current env
    python scripts/check_arm64_binaries.py PATH [PATH..]  # scan specific roots
    python scripts/check_arm64_binaries.py --allow foo.dll --allow bar.dll
    python scripts/check_arm64_binaries.py --json

On non-Windows hosts there are no PE binaries to validate, so the script reports
"nothing to scan" and exits 0 (the check only has teeth on the target hardware).
"""

from __future__ import annotations

import argparse
import json
import site
import sys
import sysconfig
from pathlib import Path

IMAGE_FILE_MACHINE_ARM64 = 0xAA64
IMAGE_FILE_MACHINE_AMD64 = 0x8664
IMAGE_FILE_MACHINE_I386 = 0x014C

_PE_SUFFIXES = (".exe", ".dll", ".pyd")

_MACHINE_NAMES = {
    IMAGE_FILE_MACHINE_ARM64: "ARM64",
    IMAGE_FILE_MACHINE_AMD64: "AMD64",
    IMAGE_FILE_MACHINE_I386: "x86",
}


def read_pe_machine(path: Path) -> int | None:
    """Return the PE machine-type word for ``path`` or ``None`` if unreadable.

    Prefers :mod:`pefile` when available; otherwise parses the PE header bytes
    directly (the same logic the app's platform detector uses).
    """
    try:
        import pefile  # type: ignore

        pe = pefile.PE(str(path), fast_load=True)
        try:
            return int(pe.FILE_HEADER.Machine)
        finally:
            pe.close()
    except ImportError:
        return _read_pe_machine_raw(path)
    except Exception:
        # Not a valid PE (resource-only DLL, corrupt stub, etc.) - skip.
        return None


def _read_pe_machine_raw(path: Path) -> int | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 64 or data[:2] != b"MZ":
        return None
    e_lfanew = int.from_bytes(data[0x3C:0x40], "little")
    if e_lfanew + 6 > len(data) or data[e_lfanew : e_lfanew + 4] != b"PE\x00\x00":
        return None
    return int.from_bytes(data[e_lfanew + 4 : e_lfanew + 6], "little")


def machine_name(machine: int | None) -> str:
    if machine is None:
        return "NOT_PE"
    return _MACHINE_NAMES.get(machine, f"UNKNOWN_0x{machine:04X}")


def default_scan_roots() -> list[Path]:
    """Interpreter prefix plus all known site-packages directories."""
    roots: list[Path] = [Path(sys.prefix)]
    if sys.base_prefix != sys.prefix:
        roots.append(Path(sys.base_prefix))
    try:
        roots.extend(Path(p) for p in site.getsitepackages())
    except AttributeError:  # virtualenvs may lack getsitepackages
        pass
    user_site = getattr(site, "getusersitepackages", lambda: None)()
    if user_site:
        roots.append(Path(user_site))
    purelib = sysconfig.get_paths().get("purelib")
    if purelib:
        roots.append(Path(purelib))

    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def iter_pe_files(roots: list[Path]):
    seen: set[Path] = set()
    for root in roots:
        if root.is_file():
            if root.suffix.lower() in _PE_SUFFIXES:
                yield root
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() in _PE_SUFFIXES and path.is_file():
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield resolved


def scan(roots: list[Path], allow: set[str]) -> dict:
    """Return a structured report of every offending (non-ARM64) binary."""
    offenders: list[dict] = []
    scanned = 0
    for path in iter_pe_files(roots):
        if path.name.lower() in allow:
            continue
        machine = read_pe_machine(path)
        if machine is None:
            continue  # not a parseable PE image
        scanned += 1
        if machine != IMAGE_FILE_MACHINE_ARM64:
            offenders.append({"path": str(path), "machine": machine_name(machine)})
    return {"scanned": scanned, "offenders": offenders}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="*", help="paths/dirs to scan (default: env)")
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="FILENAME",
        help="basename to exempt (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args(argv)

    if sys.platform != "win32" and not args.roots:
        msg = "non-Windows host: no PE binaries to validate (skipping)"
        print(json.dumps({"skipped": True, "reason": msg}) if args.json else msg)
        return 0

    roots = [Path(r) for r in args.roots] if args.roots else default_scan_roots()
    allow = {name.lower() for name in args.allow}
    report = scan(roots, allow)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Scanned {report['scanned']} PE binaries across {len(roots)} root(s).")
        for offender in report["offenders"]:
            print(f"  NON-ARM64: {offender['machine']:>8}  {offender['path']}")

    if report["offenders"]:
        count = len(report["offenders"])
        print(
            f"\nFAIL: {count} non-ARM64 binary/binaries detected. "
            "Native ARM64 wheels/executables are required on this target.",
            file=sys.stderr,
        )
        return 1
    print("OK: all scanned native binaries are ARM64.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
