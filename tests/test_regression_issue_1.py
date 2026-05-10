"""Regression tests for Issue #1: critical CLI crashes.

Each test pins a previously-broken code path so the bug cannot reappear silently.
"""

import json
import os
from pathlib import Path

import pytest

from src.config import parse_and_merge_args, validate_config
from src.history_report import load_sync_history


def test_validate_config_with_updated_after_does_not_raise_nameerror():
    """Regression: src/config.py used datetime.strptime without importing datetime."""
    opts = {
        "username": "octocat",
        "max_workers": 5,
        "min_stars": 0,
        "updated_after": "2024-01-01",
    }
    errors, _ = validate_config(opts)
    assert not any("date format" in e for e in errors)


def test_validate_config_rejects_bad_updated_after():
    opts = {
        "username": "octocat",
        "max_workers": 5,
        "min_stars": 0,
        "updated_after": "not-a-date",
    }
    errors, _ = validate_config(opts)
    assert any("date format" in e or "Invalid" in e for e in errors)


def test_parse_and_merge_args_does_not_attribute_error_on_min_stars(tmp_path, monkeypatch):
    """Regression: typo args.min_starts crashed every CLI invocation."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("github:\n  username: yamluser\n")
    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--config", str(config_file), "--username", "cli-user"],
    )
    opts = parse_and_merge_args()
    assert opts["username"] == "cli-user"
    assert opts["min_stars"] == 0


def test_parse_and_merge_args_min_stars_cli_overrides(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("filter:\n  min_stars: 10\n")
    monkeypatch.setattr(
        "sys.argv",
        ["main.py", "--config", str(config_file), "--username", "u", "--min-stars", "42"],
    )
    opts = parse_and_merge_args()
    assert opts["min_stars"] == 42


def test_load_sync_history_with_non_dict_payload_does_not_raise(tmp_path):
    """Regression: history_report.py called logger.warning without importing logger."""
    history_file = tmp_path / "last_sync.json"
    history_file.write_text(json.dumps(["unexpected", "list"]))
    result = load_sync_history(str(tmp_path))
    assert result == {}
