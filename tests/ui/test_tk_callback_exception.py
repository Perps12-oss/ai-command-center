"""C2: CommandPaletteApp surfaces unhandled Tk callback exceptions."""

from __future__ import annotations

from unittest.mock import MagicMock

from ai_command_center.ui.app import CommandPaletteApp


def test_on_tk_callback_exception_logs_and_toasts(monkeypatch) -> None:
    logged: list[tuple] = []

    def fake_error(msg, *args, **kwargs):
        logged.append((msg, kwargs.get("exc_info")))

    monkeypatch.setattr("ai_command_center.ui.app.logger.error", fake_error)

    app = CommandPaletteApp.__new__(CommandPaletteApp)
    toast = MagicMock()
    app._toast = toast

    exc = RuntimeError
    val = RuntimeError("boom-detail")
    tb = None
    app._on_tk_callback_exception(exc, val, tb)

    assert logged and "Unhandled Tk callback error" in logged[0][0]
    toast.show.assert_called_once()
    args, kwargs = toast.show.call_args
    assert "boom-detail" in args[0]
    assert kwargs.get("kind") == "error"


def test_on_tk_callback_exception_without_toast_still_logs(monkeypatch) -> None:
    logged: list[str] = []
    monkeypatch.setattr(
        "ai_command_center.ui.app.logger.error",
        lambda msg, *a, **k: logged.append(msg),
    )
    app = CommandPaletteApp.__new__(CommandPaletteApp)
    app._toast = None
    app._on_tk_callback_exception(ValueError, ValueError("x"), None)
    assert logged
