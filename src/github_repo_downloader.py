import os
import signal
import sys
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.logger import logger
from src.config import parse_and_merge_args
from src.api import get_repos
from src.history_report import (
    load_sync_history,
    save_sync_history,
    generate_report,
    check_disk_space,
    get_stats_summary
)
from src.downloader import download_zip, clone_git


_console = None


def _get_console():
    global _console
    if _console is None:
        from rich.console import Console
        _console = Console()
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


def display_preview(repos, opts):
    """Display dry-run preview table"""
    from rich.table import Table

    console = _get_console()
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
    for idx, r in enumerate(repos[:50], 1):  # Show max 50 in preview
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
            desc
        )
    
    console.print(table)
    
    if len(repos) > 50:
        console.print(f"[dim]... and {len(repos) - 50} more repositories[/dim]")
    
    console.print(f"\n[bold]Total:[/bold] {len(repos)} repositories")
    console.print(f"[bold]Estimated Size:[/bold] {total_size_kb / 1024:.2f} MB (based on API data)")
    console.print(f"[bold]Mode:[/bold] {opts['mode'].upper()}")
    console.print(f"[bold]Save Path:[/bold] {os.path.abspath(opts['save_path'])}\n")


def run():
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.table import Table

    console = _get_console()

    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        opts = parse_and_merge_args()
    except ValueError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        return
    
    if not opts['username']:
        console.print("[red]❌ Username is required! Provide it via config or arguments.[/red]")
        console.print("[dim]Example: uv run main.py --username octocat[/dim]\n")
        return
    
    token_display = mask_token(opts.get('token'))
    console.print(f"\n[bold cyan]🚀 PyScript-GitHubRepo v0.1.0[/bold cyan]")
    console.print(f"[dim]User: {opts['username']} | Token: {token_display} | Mode: {opts['mode']}[/dim]\n")
    
    console.print(f"[cyan]🔍 Fetching repositories for: {opts['username']}...[/cyan]")
    repos = get_repos(
        opts['username'],
        opts['token'],
        opts['language'],
        opts['min_stars'],
        opts['updated_after'],
        opts['max_repos']
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
        return
    
    if opts.get('dry_run'):
        display_preview(repos, opts)
        console.print("[bold green]💡 Dry run complete! Use without --dry-run to actually download.[/bold green]\n")
        return
    
    save_path_abs = os.path.abspath(opts['save_path'])
    os.makedirs(opts['save_path'], exist_ok=True)
    
    has_space, free_gb, required_gb = check_disk_space(opts['save_path'])
    if not has_space:
        console.print(f"\n[red]❌ Insufficient disk space![/red]")
        console.print(f"[red]   Available: {free_gb:.2f} GB | Recommended minimum: {required_gb:.2f} GB[/red]\n")
        return
    elif free_gb < required_gb * 2:
        console.print(f"[yellow]⚠️  Low disk space: {free_gb:.2f} GB available[/yellow]")
    
    history = load_sync_history(opts['save_path'])
    
    statuses = {}
    stats = {"success": 0, "failed": 0, "skipped": 0}
    stats_lock = threading.Lock()
    start_time = datetime.now()
    
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
        
        overall_task = progress.add_task(
            "[bold blue]Overall Progress",
            total=len(repos)
        )
        
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
                    
    save_sync_history(opts['save_path'], history)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
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
        stats['success'], stats['failed'], stats['skipped'], duration
    )


if __name__ == '__main__':
    run()
