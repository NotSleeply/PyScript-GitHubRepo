import os
import json
import csv
import shutil
from datetime import datetime

from src.logger import logger


_console = None


def _get_console():
    global _console
    if _console is None:
        from rich.console import Console
        _console = Console()
    return _console

def check_disk_space(path, required_mb=1024):
    """Check if there's enough disk space available"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    
    total, used, free = shutil.disk_usage(path)
    free_gb = free / (1024**3)
    required_gb = required_mb / 1024
    
    if free < required_mb * 1024 * 1024:
        return False, free_gb, required_gb
    return True, free_gb, required_gb


def load_sync_history(save_path):
    history_file = os.path.join(save_path, "last_sync.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    logger.warning("Invalid history file format, starting fresh")
                    return {}
        except (json.JSONDecodeError, IOError) as e:
            _get_console().print(f"[yellow]Warning: Could not load sync history: {e}[/yellow]")
            return {}
    return {}


def save_sync_history(save_path, history):
    os.makedirs(save_path, exist_ok=True)
    history_file = os.path.join(save_path, "last_sync.json")
    temp_file = history_file + '.tmp'
    
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)
        os.replace(temp_file, history_file)
    except IOError as e:
        _get_console().print(f"[red]Error saving history: {e}[/red]")


def generate_report(repos, statuses, stats, duration, opts):
    format_type = opts.get('report_format', 'markdown').lower()
    out_dir = opts.get('report_dir', '.')
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format_type == 'csv':
        filepath = os.path.join(out_dir, f"repo_report_{ts}.csv")
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Name", "Description", "Language", "Stars", "Updated At",
                "Local Path", "Status", "Size (if available)"
            ])
            for r in repos:
                name = r['name']
                writer.writerow([
                    name,
                    r.get('description', '')[:100],  # Truncate long descriptions
                    r.get('language', ''),
                    r.get('stargazers_count', 0),
                    r.get('updated_at', ''),
                    os.path.join(opts['save_path'], name),
                    statuses.get(name, "unknown"),
                    r.get('size', 'N/A')
                ])
                
    elif format_type == 'json':
        filepath = os.path.join(out_dir, f"repo_report_{ts}.json")
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "statistics": stats,
            "repositories": []
        }
        for r in repos:
            name = r['name']
            report_data["repositories"].append({
                "name": name,
                "description": r.get('description', ''),
                "language": r.get('language', ''),
                "stars": r.get('stargazers_count', 0),
                "updated_at": r.get('updated_at', ''),
                "local_path": os.path.join(opts['save_path'], name),
                "status": statuses.get(name, "unknown"),
                "size": r.get('size', None)
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
            
    else:  # markdown (default)
        filepath = os.path.join(out_dir, f"repo_report_{ts}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Repositories Download Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Repositories:** {len(repos)}\n")
            f.write(f"- **Successful:** {stats.get('success', 0)}\n")
            f.write(f"- **Failed:** {stats.get('failed', 0)}\n")
            f.write(f"- **Skipped:** {stats.get('skipped', 0)}\n")
            f.write(f"- **Duration:** {duration:.2f} seconds\n\n")
            
            success_rate = (stats.get('success', 0) / len(repos) * 100) if repos else 0
            f.write(f"- **Success Rate:** {success_rate:.1f}%\n\n")
            
            f.write("## Repository Details\n\n")
            f.write("| Name | Description | Language | Stars | Updated | Status |\n")
            f.write("| --- | --- | --- | --- | --- | --- |\n")
            
            for r in repos:
                name = r['name']
                desc = str(r.get('description', ''))[:80].replace('\n', ' ')
                lang = r.get('language', 'N/A')
                stars = r.get('stargazers_count', 0)
                updated = r.get('updated_at', 'N/A')[:10]
                status = statuses.get(name, "unknown")
                
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'skipped': '⏭️'
                }.get(status, '❓')
                
                f.write(f"| {name} | {desc} | {lang} | {stars} | {updated} | {status_emoji} {status} |\n")
                
    _get_console().print(f"[bold green]✅ Report generated: {filepath}[/bold green]")
    return filepath


def get_stats_summary(stats, total_repos, duration):
    """Generate human-readable statistics summary"""
    summary = {
        'total': total_repos,
        'success': stats.get('success', 0),
        'failed': stats.get('failed', 0),
        'skipped': stats.get('skipped', 0),
        'duration': duration,
        'success_rate': 0,
        'throughput': 0
    }
    
    if total_repos > 0:
        summary['success_rate'] = (summary['success'] / total_repos) * 100
    
    if duration > 0:
        processed = summary['success'] + summary['failed']
        summary['throughput'] = processed / duration  # repos per second
        
    return summary
