"""Orchestration layer: wire config → API → per-repo processing → history →
reports. Concurrency lives here. Presentation (rich UI vs. JSON) is
delegated to the cli/ layer via callbacks and a pluggable progress object.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from src.core.processor import process_repo
from src.log import get_logger

logger = get_logger("core.orchestrator")


# Module-level interrupt flag so signal handler (registered once in run())
# can flip it from outside any thread.
_interrupt = False


def is_interrupted() -> bool:
    return _interrupt


def mark_interrupted():
    global _interrupt
    _interrupt = True


def reset_interrupt():
    """For testing — reset between runs in the same process."""
    global _interrupt
    _interrupt = False


def execute_downloads(repos, opts, history, progress):
    """Run the concurrent download loop. Returns (statuses, stats, duration)."""
    statuses = {}
    stats = {"success": 0, "failed": 0, "skipped": 0}
    stats_lock = threading.Lock()
    start_time = datetime.now()

    overall_task = progress.add_task("[bold blue]Overall Progress", total=len(repos))

    with ThreadPoolExecutor(max_workers=opts['max_workers']) as executor:
        futures = [
            executor.submit(
                process_repo,
                repo, opts, history, progress, overall_task,
                stats, stats_lock, is_interrupted,
            )
            for repo in repos
        ]

        for future in as_completed(futures):
            if _interrupt:
                break
            repo, status, new_updated_at = future.result()
            statuses[repo['name']] = status
            if status in ('success', 'skipped'):
                history[repo['name']] = {"updated_at": new_updated_at}

    duration = (datetime.now() - start_time).total_seconds()
    return statuses, stats, duration


def mask_token(token):
    if not token or len(token) < 12:
        return "***"
    return f"{token[:4]}...{token[-4:]}"
