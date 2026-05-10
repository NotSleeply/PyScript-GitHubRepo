"""CLI layer: argparse, signal handling, dispatch to human or JSON runner.

Consumed by the project entry point (main.py → src.cli.entry.run)."""

import signal
import sys

from src.cli.human_runner import run_human
from src.cli.json_runner import emit_json, run_json
from src.config import parse_and_merge_args
from src.core import mark_interrupted
from src.log import setup_logger


def _signal_handler(signum, frame):
    from rich.console import Console

    console = Console(stderr=True)
    if not getattr(_signal_handler, "_fired", False):
        console.print("\n[yellow]⚠️  Interrupt received, finishing current tasks...[/yellow]")
        console.print("[yellow]Press Ctrl+C again to force exit.[/yellow]")
        _signal_handler._fired = True
        mark_interrupted()
    else:
        console.print("[red]❌ Force exiting...[/red]")
        sys.exit(1)


def _emit_human_error(message: str):
    from rich.console import Console

    Console(stderr=True).print(f"[red]{message}[/red]")


def run():
    """CLI entry point. Parses args, dispatches to human/JSON runner, exits
    with the runner's status code."""
    signal.signal(signal.SIGINT, _signal_handler)

    json_mode_requested = "--json" in sys.argv

    try:
        opts = parse_and_merge_args()
    except ValueError as e:
        if json_mode_requested:
            emit_json({"status": "error", "error": "config_invalid", "message": str(e)})
        else:
            _emit_human_error(f"Configuration Error: {e}")
        sys.exit(1)

    # Reconfigure logging for verbose mode (idempotent).
    setup_logger(verbose=bool(opts.get('verbose')))

    if not opts['username']:
        if opts.get('json_output'):
            emit_json({
                "status": "error",
                "error": "username_required",
                "message": "Username is required (use --username or set in config).",
            })
        else:
            _emit_human_error("❌ Username is required! Provide it via --username or config.")
        sys.exit(1)

    exit_code = run_json(opts) if opts.get('json_output') else run_human(opts)
    sys.exit(exit_code)
