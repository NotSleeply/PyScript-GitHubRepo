"""Backward-compatibility shim. Real implementation lives in src.reports package."""

from src.reports.generator import generate_report  # noqa: F401
from src.reports.history import load_sync_history, save_sync_history  # noqa: F401
from src.reports.stats import check_disk_space, get_stats_summary  # noqa: F401
