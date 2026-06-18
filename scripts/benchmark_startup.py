#!/usr/bin/env python3
"""Phase 0 baseline: cold-start timing and RAM snapshot logged to baseline.json."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_command_center.platform.detector import (  # noqa: E402
    get_baseline_log_path,
    get_ram_mb,
    is_arm64,
    write_baseline_log,
)


def main() -> int:
    if not is_arm64():
        print("benchmark_startup: FAIL — native ARM64 Python required")
        return 1

    t0 = time.perf_counter()
    import ai_command_center  # noqa: F401

    import_ms = (time.perf_counter() - t0) * 1000

    log_path = write_baseline_log(
        package_import_ms=import_ms,
        extra={"phase": 0, "benchmark": "startup"},
    )

    ram = get_ram_mb()
    print(f"benchmark_startup: package import {import_ms:.2f} ms")
    print(
        f"benchmark_startup: RAM total {ram['total_gb']} GB, "
        f"available {ram['available_gb']} GB"
    )
    print(f"benchmark_startup: logged -> {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
