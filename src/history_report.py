import os
import json
import csv
from datetime import datetime
from rich.console import Console

console = Console()

def load_sync_history(save_path):
    history_file = os.path.join(save_path, "last_sync.json")
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_sync_history(save_path, history):
    os.makedirs(save_path, exist_ok=True)
    history_file = os.path.join(save_path, "last_sync.json")
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)

def generate_report(repos, statuses, opts):
    format = opts.get('report_format', 'markdown').lower()
    out_dir = opts.get('report_dir', '.')
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format == 'csv':
        filepath = os.path.join(out_dir, f"repo_report_{ts}.csv")
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Description", "Language", "Stars", "Updated At", "Local Path", "Status"])
            for r in repos:
                name = r['name']
                writer.writerow([
                    name,
                    r.get('description', ''),
                    r.get('language', ''),
                    r.get('stargazers_count', 0),
                    r.get('updated_at', ''),
                    os.path.join(opts['save_path'], name),
                    statuses.get(name, "unknown")
                ])
    else:
        filepath = os.path.join(out_dir, f"repo_report_{ts}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Repositories Download Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("| Name | Description | Language | Stars | Updated At | Path | Status |\n")
            f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
            for r in repos:
                name = r['name']
                desc = str(r.get('description', '')).replace('\n', ' ')
                lang = r.get('language', '')
                stars = r.get('stargazers_count', 0)
                updated = r.get('updated_at', '')
                path = os.path.join(opts['save_path'], name)
                status = statuses.get(name, "unknown")
                f.write(f"| {name} | {desc} | {lang} | {stars} | {updated} | `{path}` | {status} |\n")
                
    console.print(f"[bold green]Report generated: {filepath}[/bold green]")
