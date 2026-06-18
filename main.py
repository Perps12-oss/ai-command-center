"""Future entry point for AI Command Center (Phase 0 stub)."""

from ai_command_center.platform.detector import get_architecture, is_arm64


def main() -> None:
    arch = get_architecture()
    print(f"AI Command Center - Phase 0 stub (arch={arch}, arm64={is_arm64()})")
    print("Run scripts/preflight_arm64.py before Phase 1.")


if __name__ == "__main__":
    main()
