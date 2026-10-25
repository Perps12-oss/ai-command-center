# Contributing (platform contract)

Developers targeting ACC v1.0:

1. Read [`docs/PLATFORM_CONTRACT.md`](docs/PLATFORM_CONTRACT.md).
2. Do not add AMD64-only native wheels unless they go through an ISA evidence row and an explicit allowlist change in `ai_command_center/platform/arm64_policy.py` (scanner, wheel_audit, and `compatibility_matrix.md` must stay aligned).
3. Inference-critical packages must be native ARM64 (`0xAA64`).
4. Run `python scripts/check_arm64_binaries.py` on Windows ARM64 before claiming a native env.
5. Linux CI is headless core only; it does not prove the ARM64 GUI.

Architecture, EventBus, and UI isolation rules remain in `AGENTS.md` and `PROJECT_CONSTITUTION_V4.md`.
