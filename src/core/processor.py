"""Per-repo processing: decide skip vs. download, dispatch to the right
backend (git / zip), update stats & progress. Concurrency and progress
bar live in the caller (orchestrator)."""

from src.github import clone_git, download_zip
from src.log import get_logger

logger = get_logger("core.processor")


def process_repo(repo, opts, history, progress, overall_task, stats, stats_lock, interrupt_flag):
    """Download or skip a single repo.

    interrupt_flag is a callable `() -> bool` so the caller can coordinate
    graceful Ctrl+C shutdown without a module-level global.
    """
    repo_name = repo['name']

    if interrupt_flag():
        return repo, "interrupted", history.get(repo_name, {}).get("updated_at")

    task_id = progress.add_task(f"Waiting {repo_name}...", total=100)

    last_updated = history.get(repo_name, {}).get("updated_at")
    current_updated = repo['updated_at']

    if last_updated == current_updated:
        progress.update(task_id, description=f"⏭️ Skipped {repo_name} (No update)", completed=100)
        with stats_lock:
            stats["skipped"] += 1
        progress.advance(overall_task)
        return repo, "skipped", current_updated

    try:
        if opts['mode'] == 'zip':
            download_zip(repo, opts, progress, task_id)
        else:
            clone_git(repo, opts, progress, task_id)

        progress.update(task_id, description=f"✅ Completed {repo_name}", completed=100)
        with stats_lock:
            stats["success"] += 1
        logger.info("Successfully processed %s", repo_name)
        status = "success"
    except Exception as e:
        progress.update(task_id, description=f"❌ Failed {repo_name}")
        with stats_lock:
            stats["failed"] += 1
        logger.error("Failed to process %s after retries: %s", repo_name, e)
        status = "failed"
        current_updated = last_updated

    progress.advance(overall_task)
    return repo, status, current_updated
