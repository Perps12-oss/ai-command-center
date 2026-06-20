"""Rendering layer stack — foundation plane + UI layers."""

from ai_command_center.ui.layer.background_canvas import BackgroundCanvas
from ai_command_center.ui.layer.background_controller import BackgroundController
from ai_command_center.ui.layer.background_spec import Z_INDEX, get_page_background
from ai_command_center.ui.layer.layer_stack import DepthLayer, PageLayerStack

__all__ = [
    "BackgroundCanvas",
    "BackgroundController",
    "DepthLayer",
    "PageLayerStack",
    "Z_INDEX",
    "get_page_background",
]
