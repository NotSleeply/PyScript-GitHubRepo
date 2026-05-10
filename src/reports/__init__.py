"""Reporting layer: incremental sync history, markdown/csv/json run reports,
disk-space preflight, stats summarization."""

from src.reports.generator import generate_report
from src.reports.history import load_sync_history, save_sync_history
from src.reports.stats import check_disk_space, get_stats_summary

__all__ = [
    "generate_report",
    "load_sync_history",
    "save_sync_history",
    "check_disk_space",
    "get_stats_summary",
]
