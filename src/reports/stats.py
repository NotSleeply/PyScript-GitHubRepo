"""Disk space pre-flight check + human-readable stats summarization."""

import os
import shutil


def check_disk_space(path, required_mb=1024):
    """Return (has_space, free_gb, required_gb). Creates the path if missing."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    _, _, free = shutil.disk_usage(path)
    free_gb = free / (1024 ** 3)
    required_gb = required_mb / 1024
    return (free >= required_mb * 1024 * 1024, free_gb, required_gb)


def get_stats_summary(stats, total_repos, duration):
    summary = {
        'total': total_repos,
        'success': stats.get('success', 0),
        'failed': stats.get('failed', 0),
        'skipped': stats.get('skipped', 0),
        'duration': duration,
        'success_rate': 0,
        'throughput': 0,
    }
    if total_repos > 0:
        summary['success_rate'] = (summary['success'] / total_repos) * 100
    if duration > 0:
        processed = summary['success'] + summary['failed']
        summary['throughput'] = processed / duration
    return summary
