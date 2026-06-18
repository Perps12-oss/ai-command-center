"""Cold-start timing stub for Phase 0+ benchmarking."""

from __future__ import annotations

import time


def main() -> None:
    t0 = time.perf_counter()
    import ai_command_center  # noqa: F401

    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"benchmark_startup: package import {elapsed_ms:.2f} ms (stub)")


if __name__ == "__main__":
    main()
