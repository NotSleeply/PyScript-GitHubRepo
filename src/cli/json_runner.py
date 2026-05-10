"""Machine-readable runner. stdout emits exactly one JSON object; stderr
carries any log/diagnostic output. Exit codes:
  0 — success / dry-run
  1 — config error, no repos, or insufficient disk
  2 — partial failure (at least one repo failed)
"""

import json
import os
import sys

from src.core import execute_downloads
from src.github import get_repos
from src.reports import (
    check_disk_space,
    generate_report,
    get_stats_summary,
    load_sync_history,
    save_sync_history,
)


class _NoopProgress:
    """Drop-in for rich.Progress when JSON mode is active. Keeps
    process_repo / download_zip / clone_git signatures unchanged."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def add_task(self, *args, **kwargs):
        return 0

    def update(self, *args, **kwargs):
        pass

    def advance(self, *args, **kwargs):
        pass


def emit_json(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _build_repo_entry(r, statuses, opts):
    name = r['name']
    return {
        "name": name,
        "status": statuses.get(name, "unknown"),
        "language": r.get('language') or None,
        "stars": r.get('stargazers_count', 0),
        "updated_at": r.get('updated_at'),
        "default_branch": r.get('default_branch'),
        "size_kb": r.get('size', 0),
        "local_path": os.path.abspath(os.path.join(opts['save_path'], name)),
    }


def run_json(opts) -> int:
    repos = get_repos(
        opts['username'],
        opts['token'],
        opts['language'],
        opts['min_stars'],
        opts['updated_after'],
        opts['max_repos'],
    )

    exclude_set = opts.get('exclude', set())
    if exclude_set:
        repos = [r for r in repos if r['name'] not in exclude_set]

    agent_metadata = None
    if opts.get('agent_filter') and repos:
        from src.agent import (
            AgentError,
            select_repositories,
        )
        try:
            repos, agent_metadata = select_repositories(
                repos,
                opts['agent_filter'],
                model=opts.get('agent_model'),
                api_key=opts.get('agent_api_key'),
            )
        except AgentError as e:
            emit_json({
                "status": "error",
                "error": e.code,
                "message": str(e),
            })
            return 1

    if not repos:
        emit_json({
            "status": "error",
            "error": "no_repositories",
            "message": "No repositories matched the filters (or API request failed). Check logs/app.log.",
            "username": opts['username'],
            **({"agent_filter": agent_metadata} if agent_metadata else {}),
        })
        return 1

    if opts.get('dry_run'):
        total_size_kb = sum(r.get('size', 0) for r in repos)
        emit_json({
            "status": "dry_run",
            "username": opts['username'],
            "mode": opts['mode'],
            "count": len(repos),
            "estimated_size_mb": round(total_size_kb / 1024, 2),
            "save_path": os.path.abspath(opts['save_path']),
            **({"agent_filter": agent_metadata} if agent_metadata else {}),
            "repositories": [
                {
                    "name": r['name'],
                    "language": r.get('language') or None,
                    "stars": r.get('stargazers_count', 0),
                    "updated_at": r.get('updated_at'),
                    "size_kb": r.get('size', 0),
                    "description": r.get('description') or None,
                }
                for r in repos
            ],
        })
        return 0

    os.makedirs(opts['save_path'], exist_ok=True)
    has_space, free_gb, required_gb = check_disk_space(opts['save_path'])
    if not has_space:
        emit_json({
            "status": "error",
            "error": "insufficient_disk_space",
            "free_gb": round(free_gb, 2),
            "required_gb": round(required_gb, 2),
        })
        return 1

    history = load_sync_history(opts['save_path'])

    with _NoopProgress() as progress:
        statuses, stats, duration = execute_downloads(repos, opts, history, progress)

    save_sync_history(opts['save_path'], history)
    report_path = generate_report(repos, statuses, stats, duration, opts)
    summary = get_stats_summary(stats, len(repos), duration)

    failed_names = sorted(n for n, s in statuses.items() if s == 'failed')
    overall_status = "ok" if stats['failed'] == 0 else "partial"

    emit_json({
        "status": overall_status,
        "username": opts['username'],
        "mode": opts['mode'],
        "save_path": os.path.abspath(opts['save_path']),
        "duration_seconds": round(duration, 2),
        "stats": {
            "total": len(repos),
            "success": summary['success'],
            "failed": summary['failed'],
            "skipped": summary['skipped'],
            "success_rate": round(summary['success_rate'], 1),
            "throughput_per_sec": round(summary['throughput'], 2),
        },
        "repositories": [_build_repo_entry(r, statuses, opts) for r in repos],
        "failed": failed_names,
        "report_path": os.path.abspath(report_path) if report_path else None,
    })

    return 2 if stats['failed'] > 0 else 0
