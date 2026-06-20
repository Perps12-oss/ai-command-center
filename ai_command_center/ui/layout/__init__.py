"""Layout compiler — schema-validated page trees."""

from ai_command_center.ui.layout.compiler import (
    APPROVED_LAYOUTS,
    LayoutCompiler,
    LayoutValidationError,
    load_background_layer,
    load_layout_schema,
    load_motion_bindings,
    load_spatial_map,
    load_style_lock,
)

__all__ = [
    "APPROVED_LAYOUTS",
    "LayoutCompiler",
    "LayoutValidationError",
    "load_background_layer",
    "load_layout_schema",
    "load_motion_bindings",
    "load_spatial_map",
    "load_style_lock",
]
