"""Launch-time identity — proves which tree/package is actually executing.

Freeze reports that lack these markers are from a stale copy (often the
legacy OneDrive tree while GitHub Desktop synced Documents/GITHUB).
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Bump when freeze/perf identity contract changes. Must match ACC_UI_FREEZE_FIX.
REQUIRED_FREEZE_FIX = "v6"


@dataclass(frozen=True)
class RuntimeIdentity:
    freeze_fix: str
    main_path: str
    cwd: str
    event_bus_path: str
    package_root: str
    git_head: str
    python_exe: str

    @property
    def is_current(self) -> bool:
        return self.freeze_fix == REQUIRED_FREEZE_FIX

    def format_lines(self) -> list[str]:
        status = "OK" if self.is_current else f"STALE want={REQUIRED_FREEZE_FIX}"
        return [
            (
                f"ACC_UI_RUNTIME freeze_fix={self.freeze_fix} status={status} "
                f"event_bus={self.event_bus_path}"
            ),
            (
                f"ACC_UI_RUNTIME main={self.main_path} cwd={self.cwd} "
                f"package={self.package_root} git={self.git_head} "
                f"python={self.python_exe}"
            ),
        ]


def _git_head(repo_dir: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if completed.returncode == 0:
            return completed.stdout.strip() or "unknown"
    except Exception:
        pass
    return "unknown"


def collect_runtime_identity(*, main_file: str | None = None) -> RuntimeIdentity:
    """Resolve freeze_fix + filesystem paths for the live process."""
    import ai_command_center
    import ai_command_center.core.event_bus as event_bus_mod
    from ai_command_center.ui.app import ACC_UI_FREEZE_FIX

    main_path = str(Path(main_file or sys.argv[0] or "").resolve())
    package_root = str(Path(ai_command_center.__file__).resolve().parent)
    repo_guess = Path(main_path).parent if main_path else Path.cwd()
    return RuntimeIdentity(
        freeze_fix=str(ACC_UI_FREEZE_FIX),
        main_path=main_path or "(unknown)",
        cwd=str(Path.cwd().resolve()),
        event_bus_path=str(Path(event_bus_mod.__file__).resolve()),
        package_root=package_root,
        git_head=_git_head(repo_guess),
        python_exe=sys.executable,
    )


def print_runtime_identity(*, main_file: str | None = None, stream=None) -> RuntimeIdentity:
    """Print identity to stdout (and flush). Returns the collected identity."""
    out = stream if stream is not None else sys.stdout
    identity = collect_runtime_identity(main_file=main_file)
    for line in identity.format_lines():
        print(line, file=out, flush=True)
    # Mirror to stderr so redirected / filtered consoles still show it.
    if out is sys.stdout:
        for line in identity.format_lines():
            print(line, file=sys.stderr, flush=True)
    return identity


def assert_event_bus_budget_format() -> bool:
    """True when EventBus budget warnings include handler= (post-#106)."""
    import ai_command_center.core.event_bus as event_bus_mod

    source = Path(event_bus_mod.__file__).read_text(encoding="utf-8")
    return "handler=%s" in source and "source=%s elapsed_ms" in source
