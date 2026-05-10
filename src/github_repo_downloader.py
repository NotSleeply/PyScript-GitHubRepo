import json
import os
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from src.api import get_repos
from src.config import parse_and_merge_args
from src.downloader import clone_git, download_zip
from src.history_report import (
    check_disk_space,
    generate_report,
    get_stats_summary,
    load_sync_history,
    save_sync_history,
)
from src.logger import logger


_console = None
_json_mode = False


def _get_console():
    """Return a cached rich Console. In JSON mode, writes go to stderr so
    stdout remains a single clean JSON object."""
    global _console
    if _console is None:
        from rich.console import Console
        _console = Console(stderr=_json_mode)
    return _console


global_interrupt = False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global global_interrupt
    console = _get_console()
    if not global_interrupt:
        console.print("\n[yellow]⚠️  Interrupt received, finishing current tasks...[/yellow]")
        console.print("[yellow]Press Ctrl+C again to force exit.[/yellow]")
        global_interrupt = True
    else:
        console.print("[red]❌ Force exiting...[/red]")
        sys.exit(1)


def mask_token(token):
    """Mask token for safe logging (show only first 4 and last 4 chars)"""
    if not token or len(token) < 12:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


class _NoopProgress:
    """Drop-in replacement for rich.Progress when JSON mode is active.

    process_repo / download_zip / clone_git all take (progress, task_id)
    and call add_task/update/advance on them. Keeping the same surface
    means we don't have to plumb json_mode flags through every helper.
    """

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


def process_repo(repo, opts, history, progress, overall_task, stats, stats_lock):
    repo_name = repo['name']

    if global_interrupt:
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


def _execute_downloads(repos, opts, history, progress):
    """Run the download loop under the given progress instance.

    Returns (statuses, stats, duration).
    """
    statuses = {}
    stats = {"success": 0, "failed": 0, "skipped": 0}
    stats_lock = threading.Lock()
    start_time = datetime.now()

    overall_task = progress.add_task("[bold blue]Overall Progress", total=len(repos))

    with ThreadPoolExecutor(max_workers=opts['max_workers']) as executor:
        futures = [
            executor.submit(process_repo, repo, opts, history, progress, overall_task, stats, stats_lock)
            for repo in repos
        ]

        for future in as_completed(futures):
            if global_interrupt:
                break
            repo, status, new_updated_at = future.result()
            statuses[repo['name']] = status
            if status in ('success', 'skipped'):
                history[repo['name']] = {"updated_at": new_updated_at}

    duration = (datetime.now() - start_time).total_seconds()
    return statuses, stats, duration


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


def _emit_json(payload):
    """Write a single JSON object to stdout. Must be the only stdout write
    in JSON mode — agents parse stdout directly."""
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _run_json(opts):
    """Machine-readable entry point. stdout emits exactly one JSON object;
    everything else (rich UI, logs, warnings) goes to stderr.

    Exit codes:
      0 — all downloads succeeded (or dry-run)
      1 — configuration error, no repos found, or insufficient disk space
      2 — at least one repo failed
    """
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

    if not repos:
        _emit_json({
            "status": "error",
            "error": "no_repositories",
            "message": "No repositories matched the filters (or API request failed). Check app.log.",
            "username": opts['username'],
        })
        return 1

    if opts.get('dry_run'):
        total_size_kb = sum(r.get('size', 0) for r in repos)
        _emit_json({
            "status": "dry_run",
            "username": opts['username'],
            "mode": opts['mode'],
            "count": len(repos),
            "estimated_size_mb": round(total_size_kb / 1024, 2),
            "save_path": os.path.abspath(opts['save_path']),
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
        _emit_json({
            "status": "error",
            "error": "insufficient_disk_space",
            "free_gb": round(free_gb, 2),
            "required_gb": round(required_gb, 2),
        })
        return 1

    history = load_sync_history(opts['save_path'])

    with _NoopProgress() as progress:
        statuses, stats, duration = _execute_downloads(repos, opts, history, progress)

    save_sync_history(opts['save_path'], history)
    report_path = generate_report(repos, statuses, stats, duration, opts)
    summary = get_stats_summary(stats, len(repos), duration)

    failed_names = sorted(n for n, s in statuses.items() if s == 'failed')
    overall_status = "ok" if stats['failed'] == 0 else "partial"

    _emit_json({
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


def _run_human(opts):
    """Human-facing entry point (original rich UI path)."""
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table

    console = _get_console()

    token_display = mask_token(opts.get('token'))
    console.print("\n[bold cyan]🚀 PyScript-GitHubRepo v0.1.0[/bold cyan]")
    console.print(f"[dim]User: {opts['username']} | Token: {token_display} | Mode: {opts['mode']}[/dim]\n")

    console.print(f"[cyan]🔍 Fetching repositories for: {opts['username']}...[/cyan]")
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
        original_count = len(repos)
        repos = [r for r in repos if r['name'] not in exclude_set]
        excluded_count = original_count - len(repos)
        console.print(f"[yellow]🚫 Excluded {excluded_count} repositories (exclude list)[/yellow]")

    console.print(f"[bold green]✅ Found {len(repos)} repositories matching criteria.[/bold green]")

    if not repos:
        console.print("[yellow]⚠️  No repositories found or API error occurred.[/yellow]")
        console.print("[dim]Check app.log for details, or adjust your filters.[/dim]\n")
        return 1

    if opts.get('dry_run'):
        _display_preview_human(repos, opts, console)
        console.print("[bold green]💡 Dry run complete! Use without --dry-run to actually download.[/bold green]\n")
        return 0

    save_path_abs = os.path.abspath(opts['save_path'])
    os.makedirs(opts['save_path'], exist_ok=True)

    has_space, free_gb, required_gb = check_disk_space(opts['save_path'])
    if not has_space:
        console.print("\n[red]❌ Insufficient disk space![/red]")
        console.print(f"[red]   Available: {free_gb:.2f} GB | Recommended minimum: {required_gb:.2f} GB[/red]\n")
        return 1
    elif free_gb < required_gb * 2:
        console.print(f"[yellow]⚠️  Low disk space: {free_gb:.2f} GB available[/yellow]")

    history = load_sync_history(opts['save_path'])

    console.print(f"\n[bold]📥 Starting download to: {save_path_abs}[/bold]")
    console.print(f"[dim]   Concurrency: {opts['max_workers']} threads[/dim]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        statuses, stats, duration = _execute_downloads(repos, opts, history, progress)

    save_sync_history(opts['save_path'], history)
    report_path = generate_report(repos, statuses, stats, duration, opts)
    summary = get_stats_summary(stats, len(repos), duration)

    console.print("\n" + "=" * 60)
    console.print("[bold green]✨ Sync Completed![/bold green]\n")

    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold")
    summary_table.add_row("⏱️  Duration", f"{duration:.2f} seconds")
    summary_table.add_row("✅ Success", f"{summary['success']} ({summary['success_rate']:.1f}%)")
    summary_table.add_row("❌ Failed", str(summary['failed']))
    summary_table.add_row("⏭️  Skipped", str(summary['skipped']))
    summary_table.add_row("📊 Throughput", f"{summary['throughput']:.2f} repos/sec")
    summary_table.add_row("📄 Report", report_path)
    console.print(summary_table)
    console.print("=" * 60 + "\n")

    if stats["failed"] > 0:
        failed_repos = [name for name, st in statuses.items() if st == 'failed']
        console.print(f"[red]⚠️  Failed repositories ({len(failed_repos)}):[/red]")
        for name in failed_repos[:10]:
            console.print(f"[red]   - {name}[/red]")
        if len(failed_repos) > 10:
            console.print(f"[red]   ... and {len(failed_repos) - 10} more[/red]")
        console.print("[dim]Check app.log for error details[/dim]\n")

    logger.info(
        "Sync completed: success=%d, failed=%d, skipped=%d, duration=%.2fs",
        stats['success'], stats['failed'], stats['skipped'], duration,
    )
    return 2 if stats['failed'] > 0 else 0


def _display_preview_human(repos, opts, console):
    from rich.table import Table

    console.print("\n[bold cyan]📋 DRY RUN MODE - Preview[/bold cyan]\n")
    table = Table(title=f"Repositories to Download: {opts['username']}")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Name", style="green", min_width=20)
    table.add_column("Language", style="yellow")
    table.add_column("Stars", justify="right", style="magenta")
    table.add_column("Updated", style="blue")
    table.add_column("Size (KB)", justify="right")
    table.add_column("Description", style="dim", max_width=50)

    total_size_kb = 0
    for idx, r in enumerate(repos[:50], 1):
        size_kb = r.get('size', 0)
        total_size_kb += size_kb
        desc = str(r.get('description', '') or 'N/A')[:47]
        table.add_row(
            str(idx),
            r['name'],
            r.get('language') or 'N/A',
            str(r.get('stargazers_count', 0)),
            r.get('updated_at', 'N/A')[:10],
            str(size_kb),
            desc,
        )

    console.print(table)
    if len(repos) > 50:
        console.print(f"[dim]... and {len(repos) - 50} more repositories[/dim]")
    console.print(f"\n[bold]Total:[/bold] {len(repos)} repositories")
    console.print(f"[bold]Estimated Size:[/bold] {total_size_kb / 1024:.2f} MB (based on API data)")
    console.print(f"[bold]Mode:[/bold] {opts['mode'].upper()}")
    console.print(f"[bold]Save Path:[/bold] {os.path.abspath(opts['save_path'])}\n")


def run():
    global _json_mode

    signal.signal(signal.SIGINT, signal_handler)

    try:
        opts = parse_and_merge_args()
    except ValueError as e:
        if "--json" in sys.argv:
            _json_mode = True
            _emit_json({"status": "error", "error": "config_invalid", "message": str(e)})
        else:
            _get_console().print(f"[red]Configuration Error: {e}[/red]")
        sys.exit(1)

    _json_mode = bool(opts.get('json_output'))

    if not opts['username']:
        if _json_mode:
            _emit_json({"status": "error", "error": "username_required", "message": "Username is required (use --username or set in config)."})
        else:
            console = _get_console()
            console.print("[red]❌ Username is required! Provide it via config or arguments.[/red]")
            console.print("[dim]Example: uv run main.py --username octocat[/dim]\n")
        sys.exit(1)

    exit_code = _run_json(opts) if _json_mode else _run_human(opts)
    sys.exit(exit_code)


# Back-compat shim: existing tests may import display_preview directly.
def display_preview(repos, opts):
    _display_preview_human(repos, opts, _get_console())


if __name__ == '__main__':
    run()
