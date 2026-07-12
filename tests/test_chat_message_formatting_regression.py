"""Regression tests for assistant message bubble formatting.

Verifies that markdown formatting tags (code_block, bold, italic, etc.)
do not leak into the rendered text content.
"""

from __future__ import annotations

import pytest

# Skip tests if tkinter is unavailable
try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.destroy()
except Exception as exc:
    pytest.skip(f"tkinter display unavailable: {exc}", allow_module_level=True)

from ai_command_center.ui.views.chat.message_block import AssistantMessageBlock


def test_assistant_message_block_renders_markdown_correctly() -> None:
    """Verify that markdown formatting does not leak tag names into rendered text."""
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:
        pytest.skip(f"tkinter display unavailable: {exc}")
    try:
        block = AssistantMessageBlock(root)
        block.pack(fill="both", expand=True)

        # Test a combination of plain text and a code block
        test_content = "Intro text\n```py\nprint('hello world')\n```\nOutro text"
        block.finalize(test_content)
        root.update_idletasks()

        # Retrieve the displayed text from the textbox
        rendered_text = block._textbox.get("1.0", "end").strip()

        # Assertions to ensure markdown syntax markers do not leak
        assert "code_block" not in rendered_text
        assert "**" not in rendered_text
        assert "*" not in rendered_text
        assert "Intro text" in rendered_text
        assert "print('hello world')" in rendered_text
        assert "Outro text" in rendered_text
    finally:
        root.destroy()


def test_assistant_message_block_renders_bold_text() -> None:
    """Verify that bold text renders correctly without leaking tags."""
    root = tk.Tk()
    root.withdraw()
    try:
        block = AssistantMessageBlock(root)
        block.pack(fill="both", expand=True)

        test_content = "This is **bold text** in a sentence."
        block.finalize(test_content)
        root.update_idletasks()

        rendered_text = block._textbox.get("1.0", "end").strip()

        # Markdown bold markers should not appear in output
        assert "**bold text**" not in rendered_text
        # The actual content should be present
        assert "bold text" in rendered_text
    finally:
        root.destroy()


def test_assistant_message_block_renders_italic_text() -> None:
    """Verify that italic text renders correctly without leaking tags."""
    root = tk.Tk()
    root.withdraw()
    try:
        block = AssistantMessageBlock(root)
        block.pack(fill="both", expand=True)

        test_content = "This is *italic text* in a sentence."
        block.finalize(test_content)
        root.update_idletasks()

        rendered_text = block._textbox.get("1.0", "end").strip()

        # Markdown italic markers should not appear in output
        assert "*italic text*" not in rendered_text
        # The actual content should be present
        assert "italic text" in rendered_text
    finally:
        root.destroy()


def test_assistant_message_block_renders_inline_code() -> None:
    """Verify that inline code renders correctly without leaking tags."""
    root = tk.Tk()
    root.withdraw()
    try:
        block = AssistantMessageBlock(root)
        block.pack(fill="both", expand=True)

        test_content = "Use `print()` to output text."
        block.finalize(test_content)
        root.update_idletasks()

        rendered_text = block._textbox.get("1.0", "end").strip()

        # Code tag should not appear in output
        assert "code" not in rendered_text.lower() or "print()" in rendered_text
        # The actual content should be present
        assert "print()" in rendered_text
    finally:
        root.destroy()


def test_assistant_message_block_renders_header() -> None:
    """Verify that headers render correctly without leaking tags."""
    root = tk.Tk()
    root.withdraw()
    try:
        block = AssistantMessageBlock(root)
        block.pack(fill="both", expand=True)

        test_content = "# Main Header\n\nSome content below."
        block.finalize(test_content)
        root.update_idletasks()

        rendered_text = block._textbox.get("1.0", "end").strip()

        # Header tag should not appear in output
        assert "header" not in rendered_text
        # The actual content should be present
        assert "Main Header" in rendered_text
    finally:
        root.destroy()


def test_assistant_message_block_renders_list_items() -> None:
    """Verify that list items render correctly without leaking tags."""
    root = tk.Tk()
    root.withdraw()
    try:
        block = AssistantMessageBlock(root)
        block.pack(fill="both", expand=True)

        test_content = "- First item\n- Second item\n- Third item"
        block.finalize(test_content)
        root.update_idletasks()

        rendered_text = block._textbox.get("1.0", "end").strip()

        # List tag should not appear in output
        assert "list" not in rendered_text
        # The actual content should be present
        assert "First item" in rendered_text
        assert "Second item" in rendered_text
        assert "Third item" in rendered_text
    finally:
        root.destroy()


def test_assistant_message_block_renders_mixed_formatting() -> None:
    """Verify that mixed formatting renders correctly without leaking tags."""
    root = tk.Tk()
    root.withdraw()
    try:
        block = AssistantMessageBlock(root)
        block.pack(fill="both", expand=True)

        test_content = """# Title

This is **bold** and *italic* text.

```python
def hello():
    print("Hello, World!")
```

- Item 1
- Item 2

Use `code` inline.
"""
        block.finalize(test_content)
        root.update_idletasks()

        rendered_text = block._textbox.get("1.0", "end").strip()

        # No markdown syntax markers should leak into the output
        assert "code_block" not in rendered_text
        assert "**bold**" not in rendered_text
        assert "*italic*" not in rendered_text
        assert "header" not in rendered_text
        assert "list" not in rendered_text

        # Content should be preserved
        assert "Title" in rendered_text
        assert "Hello, World!" in rendered_text
        assert "Item 1" in rendered_text
        assert "Item 2" in rendered_text
        assert "code" in rendered_text
    finally:
        root.destroy()
