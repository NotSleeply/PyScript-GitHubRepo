"""Persistent sync history: tracks `updated_at` per repo so re-runs can skip
unchanged repos. Atomic write via temp file + os.replace."""

import json
import os

from src.log import get_logger

logger = get_logger("reports.history")


_HISTORY_FILE = "last_sync.json"


def _get_console():
    from rich.console import Console
    return Console()


def load_sync_history(save_path):
    history_file = os.path.join(save_path, _HISTORY_FILE)
    if not os.path.exists(history_file):
        return {}
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        logger.warning("Invalid history file format, starting fresh")
        return {}
    except (json.JSONDecodeError, IOError) as e:
        _get_console().print(f"[yellow]Warning: Could not load sync history: {e}[/yellow]")
        return {}


def save_sync_history(save_path, history):
    os.makedirs(save_path, exist_ok=True)
    history_file = os.path.join(save_path, _HISTORY_FILE)
    temp_file = history_file + '.tmp'
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)
        os.replace(temp_file, history_file)
    except IOError as e:
        _get_console().print(f"[red]Error saving history: {e}[/red]")
