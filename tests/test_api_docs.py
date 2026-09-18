"""Keep the API reference anchored to the public modules."""

from pathlib import Path

from agent_undo.hooks import run_post_tool_hook, run_pre_tool_hook, shell_wrapper
from agent_undo.journal import Journal
from agent_undo.rollback import RollbackGenerator, preview_rollback


def test_api_reference_covers_public_entry_points() -> None:
    api_reference = (Path(__file__).parents[1] / "docs" / "api.md").read_text()

    for symbol in (
        "Journal",
        "record",
        "checkpoint",
        "get_session_ops",
        "RollbackGenerator",
        "generate",
        "preview_rollback",
        "run_pre_tool_hook",
        "run_post_tool_hook",
        "shell_wrapper",
    ):
        assert f"`{symbol}" in api_reference or f"`{symbol}(" in api_reference


def test_documented_entry_points_are_importable() -> None:
    assert callable(Journal)
    assert callable(RollbackGenerator)
    assert callable(preview_rollback)
    assert callable(run_pre_tool_hook)
    assert callable(run_post_tool_hook)
    assert callable(shell_wrapper)
