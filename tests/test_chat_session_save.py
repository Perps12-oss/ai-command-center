"""Session save/update callbacks used by chat new-session flow."""

from __future__ import annotations

import unittest

from ai_command_center.ui.views.chat.session_store import SessionStore


class SessionStoreSaveTests(unittest.TestCase):
    def test_first_save_calls_on_add(self) -> None:
        store = SessionStore()
        store.append_message("user", "Hello world")
        added: list[tuple[str, str, str]] = []
        updated: list[tuple[str, str, str]] = []

        store.save_current_session(
            on_add=lambda sid, title, ts: added.append((sid, title, ts)),
            on_update=lambda sid, title, ts: updated.append((sid, title, ts)),
        )

        self.assertEqual(1, len(added))
        self.assertEqual([], updated)
        self.assertEqual("Hello world", added[0][1])

    def test_second_save_calls_on_update(self) -> None:
        store = SessionStore()
        store.append_message("user", "First message")
        store.save_current_session(on_add=lambda *_: None, on_update=lambda *_: None)
        store.append_message("assistant", "Reply")
        updated: list[tuple[str, str, str]] = []

        store.save_current_session(
            on_add=lambda *_: None,
            on_update=lambda sid, title, ts: updated.append((sid, title, ts)),
        )

        self.assertEqual(1, len(updated))
        self.assertEqual("First message", updated[0][1])

    def test_empty_history_skips_callbacks(self) -> None:
        store = SessionStore()
        called = {"add": False, "update": False}

        store.save_current_session(
            on_add=lambda *_: called.__setitem__("add", True),
            on_update=lambda *_: called.__setitem__("update", True),
        )

        self.assertFalse(called["add"])
        self.assertFalse(called["update"])

    def test_new_session_rotates_id_and_clears_history(self) -> None:
        store = SessionStore()
        first_id = store.session_id
        store.append_message("user", "Hi")
        new_id = store.start_new_session()

        self.assertNotEqual(first_id, new_id)
        self.assertEqual([], store.history)


if __name__ == "__main__":
    unittest.main()
