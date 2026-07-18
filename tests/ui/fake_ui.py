"""Headless UI test helpers.

Provides fake ``customtkinter`` / ``tkinter`` modules and imports the Phase 11A UI
components against them so projection tests can run without a real Tk display.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Callable


def _make_widget_class(name: str, button: bool = False, textbox: bool = False):
    """Return a fake CustomTkinter widget class."""

    class FakeWidget:
        def __init__(self, master=None, **kwargs) -> None:
            self._master = master
            self._kwargs = kwargs
            self._children: list[object] = []
            self._kwargs.setdefault("text", "")

        def cget(self, key: str):
            return self._kwargs.get(key, "")

        def configure(self, **kwargs) -> None:
            self._kwargs.update(kwargs)

        def config(self, **kwargs) -> None:
            self.configure(**kwargs)

        def pack(self, **kwargs) -> None:
            if self._master is not None:
                try:
                    self._master._children.append(self)
                except Exception:
                    pass

        def grid(self, **kwargs) -> None:
            self.pack(**kwargs)

        def place(self, **kwargs) -> None:
            pass

        def pack_forget(self) -> None:
            pass

        def grid_forget(self) -> None:
            pass

        def destroy(self) -> None:
            pass

        def bind(self, *args, **kwargs) -> None:
            pass

        def unbind(self, *args, **kwargs) -> None:
            pass

        def after(self, *args, **kwargs) -> None:
            return None

        def update(self) -> None:
            pass

        def update_idletasks(self) -> None:
            pass

        def focus(self) -> None:
            pass

        def winfo_children(self):
            return self._children

        def winfo_width(self) -> int:
            return 0

        def winfo_height(self) -> int:
            return 0

        def winfo_reqwidth(self) -> int:
            return 0

        def winfo_reqheight(self) -> int:
            return 0

        def winfo_x(self) -> int:
            return 0

        def winfo_y(self) -> int:
            return 0

        def winfo_rootx(self) -> int:
            return 0

        def winfo_rooty(self) -> int:
            return 0

        def winfo_pointerx(self) -> int:
            return 0

        def winfo_pointery(self) -> int:
            return 0

        def __getattr__(self, name: str) -> Callable:
            return lambda *args, **kwargs: None

    if button:
        class FakeButton(FakeWidget):
            def invoke(self) -> None:
                command = self._kwargs.get("command")
                if callable(command):
                    command()

        return FakeButton

    if textbox:
        class FakeTextbox(FakeWidget):
            def get(self, *args, **kwargs) -> str:
                return self._kwargs.get("text", "")

            def insert(self, *args, **kwargs) -> None:
                pass

            def delete(self, *args, **kwargs) -> None:
                pass

            def see(self, *args, **kwargs) -> None:
                pass

            def configure(self, state=None, **kwargs) -> None:
                if state is not None:
                    kwargs["state"] = state
                super().configure(**kwargs)

        return FakeTextbox

    return FakeWidget


def _build_fake_customtkinter() -> types.ModuleType:
    mod = types.ModuleType("customtkinter")
    mod.CTk = _make_widget_class("CTk")
    mod.CTkFrame = _make_widget_class("CTkFrame")
    mod.CTkLabel = _make_widget_class("CTkLabel")
    mod.CTkButton = _make_widget_class("CTkButton", button=True)
    mod.CTkFont = lambda *args, **kwargs: args or ("Arial", 12)
    mod.CTkImage = lambda *args, **kwargs: _make_widget_class("CTkImage")()
    mod.CTkCanvas = _make_widget_class("CTkCanvas")
    mod.CTkScrollableFrame = _make_widget_class("CTkScrollableFrame")
    mod.CTkEntry = _make_widget_class("CTkEntry")
    mod.CTkTextbox = _make_widget_class("CTkTextbox", textbox=True)
    mod.CTkOptionMenu = _make_widget_class("CTkOptionMenu")
    mod.CTkSwitch = _make_widget_class("CTkSwitch")
    mod.CTkProgressBar = _make_widget_class("CTkProgressBar")
    mod.CTkSlider = _make_widget_class("CTkSlider")
    mod.CTkTabview = _make_widget_class("CTkTabview")
    mod.CTkComboBox = _make_widget_class("CTkComboBox")
    mod.CTkCheckBox = _make_widget_class("CTkCheckBox")
    mod.CTkRadioButton = _make_widget_class("CTkRadioButton")
    mod.CTkSegmentedButton = _make_widget_class("CTkSegmentedButton")

    mod.ThemeManager = types.SimpleNamespace(
        theme={"color": {}},
        load_theme=lambda *a, **k: None,
        get_color=lambda *a, **k: "#000000",
    )

    class _Var:
        def __init__(self, value=None, *args, **kwargs):
            self._value = value

        def get(self):
            return self._value

        def set(self, value) -> None:
            self._value = value

        def trace(self, *args, **kwargs) -> None:
            pass

        def trace_add(self, *args, **kwargs) -> None:
            pass

        def trace_remove(self, *args, **kwargs) -> None:
            pass

    mod.StringVar = _Var
    mod.BooleanVar = _Var
    mod.IntVar = _Var
    mod.DoubleVar = _Var

    mod.END = "end"
    mod.INSERT = "insert"
    mod.LEFT = "left"
    mod.RIGHT = "right"
    mod.TOP = "top"
    mod.BOTTOM = "bottom"
    mod.X = "x"
    mod.Y = "y"
    mod.BOTH = "both"
    mod.W = "w"
    mod.E = "e"
    mod.N = "n"
    mod.S = "s"
    mod.NW = "nw"
    mod.NE = "ne"
    mod.SW = "sw"
    mod.SE = "se"
    mod.CENTER = "center"
    mod.NORMAL = "normal"
    mod.DISABLED = "disabled"
    mod.HIDDEN = "hidden"
    mod.RAISED = "raised"
    mod.SUNKEN = "sunken"
    mod.FLAT = "flat"
    mod.GROOVE = "groove"
    mod.RIDGE = "ridge"
    mod.SOLID = "solid"
    mod.DOTTED = "dotted"
    mod.DASHED = "dashed"
    mod.ARC = "arc"
    mod.CHORD = "chord"
    mod.PIESLICE = "pieslice"
    mod.FIRST = "first"
    mod.LAST = "last"
    mod.ALL = "all"
    mod.CURRENT = "current"

    mod.get_appearance_mode = lambda: "Dark"
    mod.set_appearance_mode = lambda *a, **k: None
    mod.set_default_color_theme = lambda *a, **k: None
    mod.deactivate_automatic_dpi_awareness = lambda *a, **k: None
    mod.enable_macos_dark_title_bar = lambda *a, **k: None
    mod.disable_macos_dark_title_bar = lambda *a, **k: None

    return mod


def _build_fake_tkinter() -> types.ModuleType:
    mod = types.ModuleType("tkinter")

    class FakeTcl:
        def eval(self, *args, **kwargs) -> str:
            return ""

    mod.Tcl = FakeTcl
    mod.TclError = Exception
    mod.Tk = _make_widget_class("Tk")
    mod.Frame = _make_widget_class("Frame")
    mod.Label = _make_widget_class("Label")
    mod.Button = _make_widget_class("Button", button=True)
    mod.Entry = _make_widget_class("Entry")
    mod.Text = _make_widget_class("Text", textbox=True)
    mod.Canvas = _make_widget_class("Canvas")
    mod.Scrollbar = _make_widget_class("Scrollbar")
    mod.Listbox = _make_widget_class("Listbox")
    mod.Menu = _make_widget_class("Menu")
    mod.Toplevel = _make_widget_class("Toplevel")
    mod.PhotoImage = _make_widget_class("PhotoImage")
    mod.Message = _make_widget_class("Message")
    mod.Radiobutton = _make_widget_class("Radiobutton")
    mod.Checkbutton = _make_widget_class("Checkbutton")
    mod.Scale = _make_widget_class("Scale")
    mod.Spinbox = _make_widget_class("Spinbox")
    mod.PanedWindow = _make_widget_class("PanedWindow")
    mod.Labelframe = _make_widget_class("Labelframe")
    mod.ttk = types.SimpleNamespace(
        Frame=_make_widget_class("Frame"),
        Label=_make_widget_class("Label"),
        Button=_make_widget_class("Button", button=True),
        Entry=_make_widget_class("Entry"),
        Treeview=_make_widget_class("Treeview"),
        Style=lambda *a, **k: types.SimpleNamespace(
            configure=lambda *a, **k: None,
            map=lambda *a, **k: None,
            lookup=lambda *a, **k: "",
        ),
    )

    class _Event:
        pass

    mod.Event = _Event
    mod.StringVar = lambda *a, **k: _build_fake_customtkinter().StringVar(*a, **k)
    mod.BooleanVar = lambda *a, **k: _build_fake_customtkinter().StringVar(*a, **k)
    mod.IntVar = lambda *a, **k: _build_fake_customtkinter().StringVar(*a, **k)
    mod.DoubleVar = lambda *a, **k: _build_fake_customtkinter().StringVar(*a, **k)

    mod.END = "end"
    mod.INSERT = "insert"
    mod.LEFT = "left"
    mod.RIGHT = "right"
    mod.TOP = "top"
    mod.BOTTOM = "bottom"
    mod.X = "x"
    mod.Y = "y"
    mod.BOTH = "both"
    mod.W = "w"
    mod.E = "e"
    mod.N = "n"
    mod.S = "s"
    mod.NW = "nw"
    mod.NE = "ne"
    mod.SW = "sw"
    mod.SE = "se"
    mod.CENTER = "center"
    mod.NORMAL = "normal"
    mod.DISABLED = "disabled"
    mod.HIDDEN = "hidden"
    mod.RAISED = "raised"
    mod.SUNKEN = "sunken"
    mod.FLAT = "flat"
    mod.GROOVE = "groove"
    mod.RIDGE = "ridge"
    mod.SOLID = "solid"
    mod.DOTTED = "dotted"
    mod.DASHED = "dashed"
    mod.ARC = "arc"
    mod.CHORD = "chord"
    mod.PIESLICE = "pieslice"
    mod.FIRST = "first"
    mod.LAST = "last"
    mod.ALL = "all"
    mod.CURRENT = "current"

    return mod


# UI modules that bind customtkinter classes at import time. Must be reloaded
# under the fake so projection tests do not inherit a prior real-Tk import.
_UI_MODULES_TO_RELOAD = (
    "ai_command_center.ui.components.glass_card",
    "ai_command_center.ui.components.status_pill",
    "ai_command_center.ui.components.top_bar",
    "ai_command_center.ui.views.command_center_view",
    "ai_command_center.ui.views.world_model.knowledge_graph_panel",
    "ai_command_center.ui.views.world_model.entity_explorer_panel",
    "ai_command_center.ui.views.world_model.selection_inspector_panel",
    "ai_command_center.ui.views.world_model.relationship_explorer_panel",
    "ai_command_center.ui.views.world_model.mutation_journal_panel",
    "ai_command_center.ui.views.world_model",
    "ai_command_center.ui.views.world_explorer_view",
    "ai_command_center.ui.components.timeline_renderer",
    "ai_command_center.ui.components.execution_timeline_scrubber",
    "ai_command_center.ui.components.docks.execution_timeline_dock",
    "ai_command_center.ui.views.execution_center.execution_list_panel",
    "ai_command_center.ui.views.execution_center.execution_timeline_panel",
    "ai_command_center.ui.views.execution_center.execution_detail_panel",
    "ai_command_center.ui.views.execution_center.receipt_viewer_panel",
    "ai_command_center.ui.views.execution_center.truth_validation_panel",
    "ai_command_center.ui.views.execution_center",
    "ai_command_center.ui.views.executions_view",
)


def _patch_and_import():
    """Swap out real tkinter/customtkinter, import UI classes, then restore."""
    orig_ctk = sys.modules.get("customtkinter")
    orig_tk = sys.modules.get("tkinter")
    saved_ui = {
        name: sys.modules.pop(name)
        for name in _UI_MODULES_TO_RELOAD
        if name in sys.modules
    }
    sys.modules["customtkinter"] = _build_fake_customtkinter()
    sys.modules["tkinter"] = _build_fake_tkinter()
    try:
        from ai_command_center.ui.views.command_center_view import CommandCenterView
        from ai_command_center.ui.components.top_bar import TopBar
        from ai_command_center.ui.views.world_explorer_view import WorldExplorerView
        from ai_command_center.ui.views.executions_view import ExecutionsView
    finally:
        # Drop fake-bound UI modules so later tests can import real Tk widgets.
        for name in _UI_MODULES_TO_RELOAD:
            sys.modules.pop(name, None)
        sys.modules.update(saved_ui)
        if orig_ctk is None:
            sys.modules.pop("customtkinter", None)
        else:
            sys.modules["customtkinter"] = orig_ctk
        if orig_tk is None:
            sys.modules.pop("tkinter", None)
        else:
            sys.modules["tkinter"] = orig_tk
    return CommandCenterView, TopBar, WorldExplorerView, ExecutionsView


CommandCenterView, TopBar, WorldExplorerView, ExecutionsView = _patch_and_import()
