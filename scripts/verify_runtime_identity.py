"""Verify the checkout you are about to launch is the freeze-fixed tree.

Run from the folder you intend to launch (no GUI):

  python scripts/verify_runtime_identity.py
  python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    main_py = ROOT / "main.py"
    text = main_py.read_text(encoding="utf-8")
    checks = {
        "main has Performance Inspector banner": "Ctrl+Shift+P for Performance Inspector" in text,
        "main calls print_runtime_identity": "print_runtime_identity" in text,
        "event_bus budget has handler=": "handler=%s" in (
            ROOT / "ai_command_center" / "core" / "event_bus.py"
        ).read_text(encoding="utf-8"),
    }

    from ai_command_center.runtime_identity import (
        REQUIRED_FREEZE_FIX,
        assert_event_bus_budget_format,
        collect_runtime_identity,
    )
    from ai_command_center.ui.app import ACC_UI_FREEZE_FIX

    identity = collect_runtime_identity(main_file=str(main_py))
    checks[f"freeze_fix == {REQUIRED_FREEZE_FIX}"] = (
        ACC_UI_FREEZE_FIX == REQUIRED_FREEZE_FIX and identity.is_current
    )
    checks["event_bus source format live"] = assert_event_bus_budget_format()
    try:
        Path(identity.event_bus_path).resolve().relative_to(ROOT.resolve())
        checks["package under this repo"] = True
    except ValueError:
        checks["package under this repo"] = False

    print(f"repo={ROOT}")
    for line in identity.format_lines():
        print(line)
    failed = False
    for name, ok in checks.items():
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}")
        if not ok:
            failed = True

    if failed:
        print(
            "\nSTALE OR WRONG TREE. Launch only from:\n"
            r"  c:\Users\S8633\Documents\GITHUB\ai-command-center"
            "\nDo not use the OneDrive legacy copy. Fully quit the tray icon first.",
            file=sys.stderr,
        )
        return 1
    print("\nIdentity OK — safe to launch: python main.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
