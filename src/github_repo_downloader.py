"""Backward-compatibility shim. Entry point lives in src.cli.entry."""

from src.cli import display_preview, emit_json, run, run_human, run_json  # noqa: F401
from src.cli.entry import _emit_human_error  # noqa: F401  (for tests that patch it)
from src.cli.json_runner import _NoopProgress, _build_repo_entry  # noqa: F401
from src.core import (  # noqa: F401
    execute_downloads as _execute_downloads,
    mark_interrupted,
    mask_token,
    process_repo,
    reset_interrupt,
)
