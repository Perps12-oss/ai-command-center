#!/usr/bin/env python3
"""Build Windows one-folder PyInstaller artifact (Track 6 P0)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if sys.platform != "win32":
        print("build_windows.py is Windows-only", file=sys.stderr)
        return 1

    repo = Path(__file__).resolve().parents[1]
    spec = repo / "packaging" / "windows" / "ai_command_center.spec"
    exe = repo / "dist" / "AICommandCenter" / "AICommandCenter.exe"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec),
        "--noconfirm",
        "--distpath",
        str(repo / "dist"),
        "--workpath",
        str(repo / "build"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=repo, check=True)

    if not exe.is_file():
        print(f"Expected artifact missing: {exe}", file=sys.stderr)
        return 1

    print(f"Build OK: {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
