"""ADR-017 — pin closed SA.mutate surface (WEA remain outside)."""

from __future__ import annotations

from ai_command_center.services import state_authority_service as sa_mod


def test_sa_supported_ops_excludes_wea_domains() -> None:
    """Live mutate ops are WM + store_memory + submit_goal only."""
    supported = sa_mod._SUPPORTED_OPS
    assert "store_memory" in supported
    assert "submit_goal" in supported
    assert "create_node" in supported
    assert "create_edge" in supported
    for forbidden in (
        "start_workflow",
        "complete_workflow",
        "append_execution_run",
        "spawn_agent",
        "cancel_agent",
    ):
        assert forbidden not in supported
