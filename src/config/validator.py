"""Validate the merged options dict. Returns (errors, warnings) lists so
callers can decide whether to print, raise, or surface as JSON."""

import re
from datetime import datetime


_GH_USERNAME_RE = re.compile(r'^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$')


def validate_config(opts):
    errors = []
    warnings = []

    if not opts.get('username'):
        errors.append("Username is required")
    else:
        if not _GH_USERNAME_RE.match(opts['username']):
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
            errors.append(
                f"Invalid date format for updated_after: {opts['updated_after']}. Use YYYY-MM-DD"
            )

    return errors, warnings
