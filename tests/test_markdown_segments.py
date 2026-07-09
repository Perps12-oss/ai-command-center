"""Tests for markdown segment tuple order (text, tag) vs renderer."""
from __future__ import annotations

import unittest

from ai_command_center.ui.markdown_view import parse_markdown


class MarkdownSegmentOrderTests(unittest.TestCase):
    def test_inline_code_segment_order_is_text_then_tag(self) -> None:
        segments = parse_markdown("Use `print('hi')` here")
        code_segments = [s for s in segments if s[1] == "code"]
        self.assertTrue(code_segments, "expected inline code segment")
        text, tag = code_segments[0]
        self.assertEqual("code", tag)
        self.assertIn("print", text)
        self.assertNotEqual(text, "code")

    def test_fenced_block_preserves_body_not_tag_name(self) -> None:
        body = "```python\nprint('hello')\n```"
        segments = parse_markdown(body)
        block_segments = [s for s in segments if s[1] == "code_block"]
        self.assertTrue(block_segments)
        text, tag = block_segments[0]
        self.assertEqual("code_block", tag)
        self.assertIn("print('hello')", text)
        self.assertNotEqual(text, "code_block")


if __name__ == "__main__":
    unittest.main()
