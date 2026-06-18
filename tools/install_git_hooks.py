#!/usr/bin/env python3
"""Install cross-platform UCGS pre-commit hook."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

HOOK_BODY = """#!/usr/bin/env python3
\"\"\"UCGS v5 pre-commit hook (auto-generated).\"\"\"

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, check=False)

def main():
    print("Running UCGS pre-commit check...")
    run([PYTHON, "tools/ucgs_runner.py"])
    gate = run([PYTHON, "tools/ucgs_ci_gate.py", ".ucgs_last.yaml"])
    if gate.returncode != 0:
        print("Commit blocked by UCGS architecture rules")
        return 1
    print("UCGS passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""


def find_git_dir(project_root: Path) -> Path | None:
    git_dir = project_root / ".git"
    if git_dir.is_dir():
        return git_dir
    return None


def install_hook(project_root: Path) -> int:
    git_dir = find_git_dir(project_root)
    if git_dir is None:
        print("No .git directory found; skipping hook install.")
        return 0

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    hook_path.write_text(HOOK_BODY, encoding="utf-8", newline="\n")

    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Installed UCGS pre-commit hook: {hook_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install UCGS git pre-commit hook")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path.cwd(),
        help="Project root containing .git",
    )
    args = parser.parse_args()
    return install_hook(args.target.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
