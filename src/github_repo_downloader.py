import os
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console

from src.logger import logger
from src.config import parse_and_merge_args
from src.api import get_repos
from src.history_report import load_sync_history, save_sync_history, generate_report
from src.downloader import download_zip, clone_git

console = Console()

def process_repo(repo, opts, history, progress, overall_task, stats, stats_lock):
    repo_name = repo['name']
    task_id = progress.add_task(f"Waiting {repo_name}...", total=100)
    
    last_updated = history.get(repo_name, {}).get("updated_at")
    current_updated = repo['updated_at']
    
    if last_updated == current_updated:
        progress.update(task_id, description=f"Skipped {repo_name} (No update)", completed=100)
        with stats_lock:
            stats["skipped"] += 1
        progress.advance(overall_task)
        return repo, "skipped", current_updated
        
    try:
        if opts['mode'] == 'zip':
            download_zip(repo, opts, progress, task_id)
        else:
            clone_git(repo, opts, progress, task_id)
            
        progress.update(task_id, description=f"[green]Completed {repo_name}[/green]", completed=100)
        with stats_lock:
            stats["success"] += 1
        logger.info(f"Successfully processed {repo_name}")
        status = "success"
    except Exception as e:
        progress.update(task_id, description=f"[red]Failed {repo_name}[/red]")
        with stats_lock:
            stats["failed"] += 1
        logger.error(f"Failed to process {repo_name} after retries: {str(e)}")
        status = "failed"
        current_updated = last_updated
        
    progress.advance(overall_task)
    return repo, status, current_updated

def run():
    opts = parse_and_merge_args()
    
    if not opts['username']:
        console.print("[red]Username is required! Provide it via config or arguments.[/red]")
        return
        
    console.print(f"[cyan]Fetching repositories for user: {opts['username']}...[/cyan]")
    repos = get_repos(opts['username'], opts['token'], opts['language'], opts['min_stars'], opts['updated_after'])
    console.print(f"[bold green]Found {len(repos)} repositories matching criteria.[/bold green]")
    
    if not repos:
        console.print("[yellow]0 repositories found or API error occurred. Check app.log for more details.[/yellow]")
        return
        
    os.makedirs(opts['save_path'], exist_ok=True)
    history = load_sync_history(opts['save_path'])
    
    statuses = {}
    stats = {"success": 0, "failed": 0, "skipped": 0}
    stats_lock = threading.Lock()
    start_time = datetime.now()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        
        overall_task = progress.add_task("[bold blue]Overall Progress", total=len(repos))
        
        with ThreadPoolExecutor(max_workers=opts['max_workers']) as executor:
            futures = [executor.submit(process_repo, repo, opts, history, progress, overall_task, stats, stats_lock) for repo in repos]
            
            for future in as_completed(futures):
                repo, status, new_updated_at = future.result()
                statuses[repo['name']] = status
                if status in ('success', 'skipped'):
                    history[repo['name']] = {"updated_at": new_updated_at}
                    
    save_sync_history(opts['save_path'], history)
    generate_report(repos, statuses, opts)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    console.print("-" * 50)
    console.print(f"[bold]✨ Sync Completed in {duration:.2f} seconds![/bold]")
    console.print(f"📊 [green]Success: {stats['success']}[/green] | [red]Failed: {stats['failed']}[/red] | [yellow]Skipped: {stats['skipped']}[/yellow]")
    console.print("-" * 50)
