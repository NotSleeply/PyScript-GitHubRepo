"""Human-facing runner with rich progress bars, emojis, and summary table.
Stdout is a UX stream, not a programmatic one; agents should use the
JSON runner instead."""

import os

from src.core import execute_downloads, mask_token
from src.github import get_repos
from src.log import get_logger
from src.reports import (
    check_disk_space,
    generate_report,
    get_stats_summary,
    load_sync_history,
    save_sync_history,
)

logger = get_logger("cli.human")


def _get_console(stderr=False):
    from rich.console import Console
    return Console(stderr=stderr)


def run_human(opts) -> int:
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
        before = len(repos)
        repos = [r for r in repos if r['name'] not in exclude_set]
        console.print(f"[yellow]🚫 Excluded {before - len(repos)} repositories (exclude list)[/yellow]")

    if opts.get('agent_filter') and repos:
        from src.agent import AgentError, select_repositories

        console.print(
            f"[magenta]🤖 Agent filter: asking {opts.get('agent_model') or 'Claude'} — "
            f"{opts['agent_filter']!r}[/magenta]"
        )
        try:
            repos, meta = select_repositories(
                repos,
                opts['agent_filter'],
                model=opts.get('agent_model'),
                api_key=opts.get('agent_api_key'),
            )
            console.print(
                f"[magenta]   → Selected {meta['selected_count']}/{meta['total_considered']}: "
                f"{meta['rationale']}[/magenta]"
            )
        except AgentError as e:
            console.print(f"[red]❌ Agent filter failed ({e.code}): {e}[/red]")
            return 1

    console.print(f"[bold green]✅ Found {len(repos)} repositories matching criteria.[/bold green]")

    if not repos:
        console.print("[yellow]⚠️  No repositories found or API error occurred.[/yellow]")
        console.print("[dim]Check logs/app.log for details, or adjust your filters.[/dim]\n")
        return 1

    if opts.get('dry_run'):
        _display_preview(repos, opts, console)
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
        statuses, stats, duration = execute_downloads(repos, opts, history, progress)

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
        console.print("[dim]Check logs/app.log for error details[/dim]\n")

    logger.info(
        "Sync completed: success=%d, failed=%d, skipped=%d, duration=%.2fs",
        stats['success'], stats['failed'], stats['skipped'], duration,
    )
    return 2 if stats['failed'] > 0 else 0


def _display_preview(repos, opts, console):
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


def display_preview(repos, opts):
    """Back-compat shim for existing callers / tests."""
    _display_preview(repos, opts, _get_console())
