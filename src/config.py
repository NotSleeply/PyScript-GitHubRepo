import os
import yaml
import argparse

def load_config(config_path):
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}

def parse_and_merge_args():
    parser = argparse.ArgumentParser(description="GitHub Repo Downloader")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--username", help="GitHub username")
    parser.add_argument("--token", help="GitHub Personal Access Token")
    parser.add_argument("--mode", choices=['zip', 'git'], help="Download mode")
    parser.add_argument("--save-path", help="Local directory to save")
    parser.add_argument("--target-ref", help="Branch or Tag (e.g., main, v1.0)")
    parser.add_argument("--keep-zip", action='store_true', default=None, help="Keep ZIP file after extraction")
    parser.add_argument("--language", help="Filter by language")
    parser.add_argument("--min-stars", type=int, help="Filter by min stars")
    parser.add_argument("--updated-after", help="Filter by updated date (YYYY-MM-DD)")
    parser.add_argument("--max-workers", type=int, help="Number of concurrent threads")
    parser.add_argument("--report-format", choices=['markdown', 'csv'], help="Report format")
    parser.add_argument("--report-dir", help="Report output directory")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    c_github = config.get('github', {})
    c_dw = config.get('download', {})
    c_filter = config.get('filter', {})
    c_conc = config.get('concurrency', {})
    c_repo = config.get('report', {})

    return {
        "username": args.username or c_github.get('username'),
        "token": args.token or c_github.get('token'),
        "mode": args.mode or c_dw.get('mode', 'git'),
        "save_path": args.save_path or c_dw.get('save_path', './repos'),
        "target_ref": args.target_ref or c_dw.get('target_ref', 'main'),
        "keep_zip": args.keep_zip if args.keep_zip is not None else c_dw.get('keep_zip', False),
        "language": args.language or c_filter.get('language'),
        "min_stars": args.min_stars if args.min_stars is not None else c_filter.get('min_stars', 0),
        "updated_after": args.updated_after or c_filter.get('updated_after'),
        "max_workers": args.max_workers or c_conc.get('max_workers', 5),
        "report_format": args.report_format or c_repo.get('format', 'markdown'),
        "report_dir": args.report_dir or c_repo.get('output_dir', '.')
    }
