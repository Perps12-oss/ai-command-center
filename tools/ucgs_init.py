#!/usr/bin/env python3
"""Bootstrap UCGS v5 kit into any project."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

KIT_DIRS = [".github", ".cursor", "tools", "ucgs.profiles"]
KIT_FILES = ["ucgs.config.yaml", ".gitignore", "README.md"]
IGNORE_NAMES = {".git", "__pycache__", ".ucgs_last.yaml", "ucgs_report.yaml"}


def kit_root() -> Path:
    return Path(__file__).resolve().parent.parent


def global_template_root() -> Path:
    return Path.home() / ".cursor" / "templates" / "ucgs-v5"


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        if any(part in IGNORE_NAMES for part in item.parts):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def merge_gitignore(target_root: Path, kit_gitignore: Path) -> None:
    target = target_root / ".gitignore"
    lines_to_add = []
    if kit_gitignore.exists():
        for line in kit_gitignore.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and stripped not in lines_to_add:
                lines_to_add.append(stripped)

    existing = set()
    if target.exists():
        existing = {line.strip() for line in target.read_text(encoding="utf-8").splitlines()}

    missing = [line for line in lines_to_add if line not in existing]
    if not missing:
        return

    suffix = "\n".join(missing)
    if target.exists() and target.read_text(encoding="utf-8").strip():
        target.write_text(target.read_text(encoding="utf-8").rstrip() + "\n" + suffix + "\n", encoding="utf-8")
    else:
        target.write_text(suffix + "\n", encoding="utf-8")


def apply_profile(target_root: Path, profile: str) -> None:
    config_path = target_root / "ucgs.config.yaml"
    if not config_path.exists():
        return
    text = config_path.read_text(encoding="utf-8")
    if "profile:" in text:
        lines = []
        for line in text.splitlines():
            if line.startswith("profile:"):
                lines.append(f"profile: {profile}")
            else:
                lines.append(line)
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        config_path.write_text(text.rstrip() + f"\nprofile: {profile}\n", encoding="utf-8")


def install_kit(source: Path, target_root: Path, profile: str, install_hooks: bool) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    same_root = source.resolve() == target_root.resolve()

    if not same_root:
        for dirname in KIT_DIRS:
            copy_tree(source / dirname, target_root / dirname)

        for filename in KIT_FILES:
            src_file = source / filename
            if src_file.exists():
                shutil.copy2(src_file, target_root / filename)

        merge_gitignore(target_root, source / ".gitignore")

    apply_profile(target_root, profile)

    if install_hooks:
        hook_installer = target_root / "tools" / "install_git_hooks.py"
        if hook_installer.exists():
            subprocess.run([sys.executable, str(hook_installer), "--target", str(target_root)], check=False)


def sync_global_template(source: Path) -> Path:
    template = global_template_root()
    template.parent.mkdir(parents=True, exist_ok=True)

    if template.exists():
        for item in template.rglob("*"):
            if item.is_file():
                try:
                    item.unlink()
                except OSError:
                    pass
        for item in sorted(template.rglob("*"), reverse=True):
            if item.is_dir():
                try:
                    item.rmdir()
                except OSError:
                    pass
    else:
        template.mkdir(parents=True, exist_ok=True)

    for item in source.rglob("*"):
        if any(part in IGNORE_NAMES for part in item.parts):
            continue
        rel = item.relative_to(source)
        target = template / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)

    return template


def main() -> int:
    parser = argparse.ArgumentParser(description="Install UCGS v5 kit into a project")
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="Target project root")
    parser.add_argument(
        "--profile",
        default="default",
        help="UCGS profile name (default, ai-command-center, ...)",
    )
    parser.add_argument("--source", type=Path, default=None, help="Kit source root")
    parser.add_argument("--no-hooks", action="store_true", help="Skip git hook installation")
    parser.add_argument(
        "--sync-global",
        action="store_true",
        help="Also sync kit to ~/.cursor/templates/ucgs-v5/",
    )
    args = parser.parse_args()

    source = (args.source or kit_root()).resolve()
    target = args.target.resolve()

    install_kit(source, target, args.profile, install_hooks=not args.no_hooks)

    if args.sync_global or source == kit_root():
        template_path = sync_global_template(source)
        print(f"Synced global template: {template_path}")

    print(f"UCGS v5 installed in: {target}")
    print(f"Profile: {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
