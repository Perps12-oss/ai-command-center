"""Chat view package — split modules for streaming, sessions, input, and search."""

# Avoid eager ChatView import: submodules (e.g. inspector tabs) must load without
# pulling the full chat shell, which would circularly import ExecutionInspector.

__all__: list[str] = []
