"""Run reports: markdown / csv / json. Each format has its own writer;
shared iteration is kept minimal on purpose — the formats diverge enough
that unifying them is more complex than useful."""

import csv
import json
import os
from datetime import datetime


def _get_console():
    from rich.console import Console
    return Console()


def _write_csv(filepath, repos, statuses, opts):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Name", "Description", "Language", "Stars", "Updated At",
            "Local Path", "Status", "Size (if available)",
        ])
        for r in repos:
            name = r['name']
            writer.writerow([
                name,
                (r.get('description') or '')[:100],
                r.get('language', ''),
                r.get('stargazers_count', 0),
                r.get('updated_at', ''),
                os.path.join(opts['save_path'], name),
                statuses.get(name, "unknown"),
                r.get('size', 'N/A'),
            ])


def _write_json(filepath, repos, statuses, stats, duration, opts):
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "duration_seconds": round(duration, 2),
        "statistics": stats,
        "repositories": [
            {
                "name": r['name'],
                "description": r.get('description', ''),
                "language": r.get('language', ''),
                "stars": r.get('stargazers_count', 0),
                "updated_at": r.get('updated_at', ''),
                "local_path": os.path.join(opts['save_path'], r['name']),
                "status": statuses.get(r['name'], "unknown"),
                "size": r.get('size'),
            }
            for r in repos
        ],
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)


def _write_markdown(filepath, repos, statuses, stats, duration):
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
            emoji = {'success': '✅', 'failed': '❌', 'skipped': '⏭️'}.get(status, '❓')
            f.write(f"| {name} | {desc} | {lang} | {stars} | {updated} | {emoji} {status} |\n")


def generate_report(repos, statuses, stats, duration, opts):
    format_type = opts.get('report_format', 'markdown').lower()
    out_dir = opts.get('report_dir', '.')
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format_type == 'csv':
        filepath = os.path.join(out_dir, f"repo_report_{ts}.csv")
        _write_csv(filepath, repos, statuses, opts)
    elif format_type == 'json':
        filepath = os.path.join(out_dir, f"repo_report_{ts}.json")
        _write_json(filepath, repos, statuses, stats, duration, opts)
    else:
        filepath = os.path.join(out_dir, f"repo_report_{ts}.md")
        _write_markdown(filepath, repos, statuses, stats, duration)

    _get_console().print(f"[bold green]✅ Report generated: {filepath}[/bold green]")
    return filepath
