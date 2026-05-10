"""User-facing layer: argparse entry, human rich UI, JSON output for agents."""

from src.cli.entry import run
from src.cli.human_runner import display_preview, run_human
from src.cli.json_runner import emit_json, run_json

__all__ = ["run", "run_human", "run_json", "emit_json", "display_preview"]
