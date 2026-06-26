import inspect
import unittest

from ai_command_center.ui.app import CommandPaletteApp


class ChatExportCallbackWiringTest(unittest.TestCase):
    def test_chat_export_callback_exists_and_accepts_history(self) -> None:
        """Regression guard: ChatView passes history to on_export; ensure the app has a handler."""
        self.assertTrue(hasattr(CommandPaletteApp, "_on_chat_export"))
        sig = inspect.signature(CommandPaletteApp._on_chat_export)
        params = list(sig.parameters)
        self.assertIn("self", params)
        self.assertIn("history", params)

    def test_chat_export_request_delegates_to_chat_export(self) -> None:
        self.assertTrue(hasattr(CommandPaletteApp, "_on_chat_export_request"))
        sig = inspect.signature(CommandPaletteApp._on_chat_export_request)
        params = list(sig.parameters)
        self.assertIn("self", params)
        self.assertNotIn("history", params)
