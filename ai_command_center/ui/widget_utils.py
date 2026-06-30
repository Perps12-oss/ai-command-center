"""Shared UI utility helpers.

Kept separate from design_system to avoid circular imports.
"""
from __future__ import annotations

import tkinter


def safe_destroy(widget) -> None:
    """Destroy a widget safely on Python 3.14 + CustomTkinter.

    CTkButton.destroy() (and some other CTk widgets) checks ``self._font``
    before verifying it is set when ``font=`` was passed as a tuple rather
    than a ``CTkFont`` object.  On Python 3.14 this raises::

        AttributeError: '_CopyBtn' object has no attribute '_font'

    Workaround: call the plain ``tkinter.Frame.destroy`` directly, which
    cascades destruction through Tkinter's own child list without hitting
    the broken CTk override.
    """
    try:
        tkinter.Frame.destroy(widget)
    except Exception:
        try:
            widget.destroy()
        except Exception:
            pass


def clear_children(container) -> None:
    """Destroy all direct children of *container* safely."""
    for child in list(container.winfo_children()):
        safe_destroy(child)
