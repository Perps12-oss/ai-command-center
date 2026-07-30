"""Regression: Tom must not flag ordinary prose as breaking changes."""

from __future__ import annotations

from tools.tom_breaking_detect import has_breaking_change_marker


def test_flush_on_destroy_is_not_breaking() -> None:
    body = (
        "Layout prefs: debounced 1.5s coalesce + flush on destroy.\n"
        "Review Approval navigates; never auto-grants."
    )
    assert has_breaking_change_marker(body) is False


def test_delete_preference_prose_is_not_breaking() -> None:
    assert has_breaking_change_marker("Users can delete a favorite from the sidebar.") is False


def test_bare_breaking_word_is_not_breaking() -> None:
    """PR prose may say Tom flagged BREAKING without the conventional marker."""
    assert has_breaking_change_marker("stop Tom false-positive BREAKING on destroy") is False


def test_backtick_documented_markers_are_not_breaking() -> None:
    """Listing intentional markers inside backticks must not self-flag the PR."""
    body = (
        "Add tools/tom_breaking_detect.py — intentional markers only "
        "(`BREAKING CHANGE`, `BREAKING:`, `MAJOR VERSION`, `API BREAK`, "
        "`DESTROY:`, `DELETE:`)."
    )
    assert has_breaking_change_marker(body) is False


def test_explicit_breaking_change_is_detected() -> None:
    assert has_breaking_change_marker("BREAKING CHANGE: remove SETTINGS_SET_REQUEST") is True
    assert has_breaking_change_marker("This is a BREAKING: API rename") is True
    assert has_breaking_change_marker("MAJOR VERSION bump required") is True
    assert has_breaking_change_marker("DESTROY: wipe vault on migrate") is True
    assert has_breaking_change_marker("DELETE: drop legacy schema table") is True


def test_plain_destroy_colon_still_detected_outside_backticks() -> None:
    body = (
        "See `tools/tom_breaking_detect.py` for docs.\n"
        "DESTROY: wipe vault on migrate\n"
    )
    assert has_breaking_change_marker(body) is True
