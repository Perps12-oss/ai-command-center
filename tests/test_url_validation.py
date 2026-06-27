"""Tests for URL scheme validation in launch actions."""

from __future__ import annotations

import pytest

from ai_command_center.core.workspace_os_actions import _launch_url


def test_launch_url_accepts_http_and_https() -> None:
    # We do not actually open the browser; just verify no ValueError.
    _launch_url({"url": "https://example.com"})
    _launch_url({"url": "http://example.com/path"})


def test_launch_url_rejects_file_scheme() -> None:
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        _launch_url({"url": "file:///etc/passwd"})


def test_launch_url_rejects_javascript_scheme() -> None:
    with pytest.raises(ValueError, match="Invalid URL scheme"):
        _launch_url({"url": "javascript:alert(1)"})


def test_launch_url_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="No URL provided"):
        _launch_url({"url": ""})
