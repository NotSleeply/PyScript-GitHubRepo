import os
import argparse
import re
import sys
from datetime import datetime
from src.logger import logger


def validate_config(opts):
    """Validate configuration options and return list of errors/warnings"""
    errors = []
    warnings = []
    
    if not opts.get('username'):
        errors.append("Username is required")
    else:
        if not re.match(r'^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$', opts['username']):
            warnings.append(f"Username '{opts['username']}' may not be valid")
    
    max_workers = opts.get('max_workers', 5)
    if max_workers < 1:
        errors.append("max_workers must be at least 1")
    elif max_workers > 50:
        warnings.append(f"max_workers={max_workers} is very high, may trigger rate limiting")

    if opts.get('max_repos', 0) < 0:
        errors.append("max_repos cannot be negative")

    if opts.get('min_stars', 0) < 0:
        errors.append("min_stars cannot be negative")

    mode = opts.get('mode', 'git')
    if mode not in ['git', 'zip']:
        errors.append(f"Invalid mode: {mode}")
    
    save_path = opts.get('save_path', './repos')
    if len(save_path) > 255:
        errors.append("save_path is too long (>255 characters)")
    
    if opts.get('updated_after'):
        try:
            datetime.strptime(opts['updated_after'], "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid date format for updated_after: {opts['updated_after']}. Use YYYY-MM-DD")
    
    return errors, warnings


def load_config(config_path):
    import yaml

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
                logger.info("Loaded configuration from %s", config_path)
                return config
        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML configuration: %s", e)
            print(f"[ERROR] Invalid YAML in {config_path}: {e}", file=sys.stderr)
            return {}
        except IOError as e:
            logger.error("Failed to read config file: %s", e)
            return {}
    else:
        logger.info("Config file not found: %s, using defaults", config_path)
        return {}


def parse_and_merge_args():
    parser = argparse.ArgumentParser(
        description="GitHub Repo Downloader - Batch download/sync repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --username octocat --language Python --min-stars 100
  %(prog)s --config myconfig.yaml --mode zip --max-repos 10
  %(prog)s --username tiangolo --dry-run  # Preview without downloading
        """
    )
    
    parser.add_argument("--config", default="config.yaml", help="Configuration file path (default: config.yaml)")
    parser.add_argument("--username", help="GitHub username or organization name")
    parser.add_argument("--token", help="GitHub Personal Access Token (optional but recommended)")
    parser.add_argument("--mode", choices=['git', 'zip'], help="Download mode: git (with history) or zip (faster)")
    parser.add_argument("--save-path", help="Local directory to save repositories")
    parser.add_argument("--target-ref", help="Branch or Tag to checkout (e.g., main, v1.0)")
    parser.add_argument("--keep-zip", action='store_true', default=None, help="Keep ZIP file after extraction (ZIP mode only)")
    parser.add_argument("--language", help="Filter by programming language (e.g., Python, JavaScript)")
    parser.add_argument("--min-stars", type=int, help="Minimum star count threshold")
    parser.add_argument("--updated-after", help="Only include repos updated after this date (YYYY-MM-DD)")
    parser.add_argument("--max-repos", type=int, help="Maximum number of repositories to download (0=unlimited)")
    parser.add_argument("--exclude", nargs='*', default=[], help="Repository names to exclude from download")
    parser.add_argument("--max-workers", type=int, help="Number of concurrent threads (default: 5)")
    parser.add_argument("--report-format", choices=['markdown', 'csv', 'json'], help="Report output format")
    parser.add_argument("--report-dir", help="Report output directory")
    parser.add_argument("--dry-run", action='store_true', help="Preview what would be downloaded without actually downloading")
    parser.add_argument("--verbose", action='store_true', help="Enable verbose/debug logging")
    parser.add_argument("--json", action='store_true', dest='json_output', help="Emit machine-readable JSON on stdout (for agent/skill use); rich UI is suppressed")
    parser.add_argument("-v", "--version", action='version', version='%(prog)s 0.1.0')
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    c_github = config.get('github', {})
    c_dw = config.get('download', {})
    c_filter = config.get('filter', {})
    c_conc = config.get('concurrency', {})
    c_repo = config.get('report', {})
    
    opts = {
        "username": args.username or c_github.get('username'),
        "token": args.token or c_github.get('token'),
        "mode": args.mode or c_dw.get('mode', 'git'),
        "save_path": args.save_path or c_dw.get('save_path', './repos'),
        "target_ref": args.target_ref or c_dw.get('target_ref', 'main'),
        "keep_zip": args.keep_zip if args.keep_zip is not None else c_dw.get('keep_zip', False),
        "language": args.language or c_filter.get('language'),
        "min_stars": args.min_stars if args.min_stars is not None else c_filter.get('min_stars', 0),
        "updated_after": args.updated_after or c_filter.get('updated_after'),
        "max_repos": args.max_repos if args.max_repos is not None else c_filter.get('max_repos', 0),
        "exclude": set(args.exclude or c_filter.get('exclude', [])),
        "max_workers": args.max_workers or c_conc.get('max_workers', 5),
        "report_format": args.report_format or c_repo.get('format', 'markdown'),
        "report_dir": args.report_dir or c_repo.get('output_dir', '.'),
        "dry_run": args.dry_run,
        "verbose": args.verbose,
        "json_output": args.json_output,
    }

    errors, warnings = validate_config(opts)

    if errors:
        for error in errors:
            print(f"[ERROR] {error}", file=sys.stderr)
        if not opts['dry_run']:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")

    if warnings and opts['verbose']:
        for warning in warnings:
            print(f"[WARNING] {warning}", file=sys.stderr)
    
    return opts
