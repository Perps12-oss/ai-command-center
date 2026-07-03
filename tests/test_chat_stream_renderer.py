"""Stream renderer buffer and markdown streaming tests (C4)."""

from __future__ import annotations

from ai_command_center.ui.markdown_view import parse_markdown
from ai_command_center.ui.views.chat.stream_renderer import StreamTextBuffer


def test_stream_text_buffer_batches_pending_delta() -> None:
    buf = StreamTextBuffer()
    assert buf.append("Hel") == "Hel"
    assert buf.append("lo") == "Hello"
    assert buf.take_pending() == "Hello"
    assert buf.take_pending() == ""
    assert buf.raw == "Hello"
    assert buf.rendered_len == 5


def test_stream_text_buffer_reset_on_finalize() -> None:
    buf = StreamTextBuffer()
    buf.append("partial")
    buf.reset("final text")
    assert buf.raw == "final text"
    assert buf.rendered_len == len("final text")
    assert buf.pending == ""


def test_parse_markdown_handles_streamed_fence() -> None:
    text = "Intro\n```py\nprint('hi')\n```\nDone"
    segments = parse_markdown(text)
    joined = "".join(seg for seg, _tag in segments)
    assert "Intro" in joined
    assert "print('hi')" in joined
    assert "Done" in joined


def test_parse_markdown_inline_styles() -> None:
    segments = parse_markdown("**bold** and *italic*")
    tags = {tag for _seg, tag in segments if tag}
    assert "bold" in tags
    assert "italic" in tags
