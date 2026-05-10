"""Regression tests for Issue #5: agent-callable skill (JSON output + SKILL.md).

These tests pin the behaviors an agent depends on:
- `--json --dry-run` emits exactly one JSON object on stdout
- `--json` puts all non-JSON text on stderr
- exit codes encode success (0) / config-or-empty (1) / partial failure (2)
- SKILL.md exists with valid frontmatter

Tests that would hit the real network use an offline mock injected via
`PYTHONPATH` override — keeping the suite fast and hermetic.
"""

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(args, extra_env=None, timeout=30):
    """Invoke `python main.py ...` in a subprocess and return (rc, out, err)."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def _write_stub_api(tmp_path, repos):
    """Create a stub that replaces `src.github.api` (the real source of
    get_repos after the Issue #7 refactor) via sitecustomize + PYTHONPATH.

    Also patches `src.api`, the back-compat shim, so tests that import
    through the old path keep working.
    """
    stub = tmp_path / "sitecustomize.py"
    payload = json.dumps(repos)
    stub.write_text(textwrap.dedent(f"""
        import sys, json
        import types as _types

        _repos = json.loads({payload!r})

        _fake_gh_api = _types.ModuleType('src.github.api')
        _fake_gh_api.get_repos = lambda *a, **kw: _repos
        sys.modules['src.github.api'] = _fake_gh_api

        _fake_api = _types.ModuleType('src.api')
        _fake_api.get_repos = lambda *a, **kw: _repos
        sys.modules['src.api'] = _fake_api
    """), encoding='utf-8')
    return stub


# ---------------------------------------------------------------------------
# SKILL.md structure
# ---------------------------------------------------------------------------

def test_skill_md_exists():
    assert (ROOT / "skill" / "SKILL.md").is_file()


def test_skill_md_has_valid_frontmatter():
    text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    # Must start with YAML frontmatter
    assert text.startswith("---\n"), "SKILL.md must begin with YAML frontmatter"
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md frontmatter block is malformed"
    body = m.group(1)
    # Required fields per Claude Agent Skill convention
    assert re.search(r"^name:\s*\S", body, re.MULTILINE), "name: field is required"
    assert re.search(r"^description:\s*\S", body, re.MULTILINE), "description: field is required"


def test_skill_md_mentions_json_flag():
    """The skill is only useful to agents if it documents --json."""
    text = (ROOT / "skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "--json" in text


# ---------------------------------------------------------------------------
# CLI --json contract
# ---------------------------------------------------------------------------

def test_json_flag_is_advertised_in_help():
    rc, out, err = _run_cli(["--help"])
    assert rc == 0
    assert "--json" in out


def test_json_error_on_missing_username():
    """No username → error JSON on stdout, exit 1, nothing on stdout except JSON.

    A missing username is caught by validate_config first, so the error code is
    `config_invalid` with the message calling out the username. If the user's
    config has a username but it fails other validation, we'd still land here —
    the username_required branch is reached only when config is otherwise valid
    (e.g. --dry-run bypasses validation)."""
    rc, out, err = _run_cli(["--json", "--config", "nonexistent.yaml"])
    assert rc == 1
    payload = json.loads(out)
    assert payload["status"] == "error"
    assert payload["error"] in ("username_required", "config_invalid")
    assert "username" in payload["message"].lower()


def test_json_error_on_invalid_date():
    """Config validation failure → error JSON, exit 1."""
    rc, out, err = _run_cli([
        "--json", "--username", "octocat", "--updated-after", "not-a-date",
        "--config", "nonexistent.yaml",
    ])
    assert rc == 1
    payload = json.loads(out)
    assert payload["status"] == "error"
    assert payload["error"] == "config_invalid"
    assert "date" in payload["message"].lower()


def test_json_dry_run_schema(tmp_path):
    """Full dry-run with a mocked API returns the documented schema."""
    repos = [
        {
            "name": "alpha",
            "language": "Python",
            "stargazers_count": 42,
            "updated_at": "2026-04-01T12:00:00Z",
            "default_branch": "main",
            "size": 1024,
            "description": "first",
            "clone_url": "https://github.com/octocat/alpha.git",
            "owner": {"login": "octocat"},
        },
        {
            "name": "beta",
            "language": None,
            "stargazers_count": 0,
            "updated_at": "2026-04-02T12:00:00Z",
            "default_branch": "main",
            "size": 512,
            "description": None,
            "clone_url": "https://github.com/octocat/beta.git",
            "owner": {"login": "octocat"},
        },
    ]
    _write_stub_api(tmp_path, repos)
    env = {"PYTHONPATH": str(tmp_path) + os.pathsep + str(ROOT)}

    rc, out, err = _run_cli(
        ["--json", "--dry-run", "--username", "octocat", "--config", "nonexistent.yaml"],
        extra_env=env,
    )
    assert rc == 0, f"expected exit 0, got {rc}. stderr={err}"
    payload = json.loads(out)
    assert payload["status"] == "dry_run"
    assert payload["username"] == "octocat"
    assert payload["count"] == 2
    assert isinstance(payload["estimated_size_mb"], (int, float))
    assert [r["name"] for r in payload["repositories"]] == ["alpha", "beta"]


def test_json_stdout_is_pure_json(tmp_path):
    """stdout must be parseable as a single JSON object. No rich codes, no logs."""
    repos = [{
        "name": "solo",
        "language": "Go",
        "stargazers_count": 1,
        "updated_at": "2026-04-01T00:00:00Z",
        "default_branch": "main",
        "size": 100,
        "description": "x",
        "clone_url": "https://github.com/x/solo.git",
        "owner": {"login": "x"},
    }]
    _write_stub_api(tmp_path, repos)
    env = {"PYTHONPATH": str(tmp_path) + os.pathsep + str(ROOT)}

    rc, out, err = _run_cli(
        ["--json", "--dry-run", "--username", "x", "--config", "nonexistent.yaml"],
        extra_env=env,
    )
    assert rc == 0
    # Should parse as exactly one JSON object (plus optional trailing whitespace)
    payload = json.loads(out.strip())
    assert isinstance(payload, dict)
    # No ANSI color codes leaked in
    assert "\x1b[" not in out, "ANSI escapes leaked into stdout in --json mode"


def test_json_no_repos_returns_exit_1(tmp_path):
    """Empty repo list → status=error/no_repositories, exit 1."""
    _write_stub_api(tmp_path, [])
    env = {"PYTHONPATH": str(tmp_path) + os.pathsep + str(ROOT)}

    rc, out, err = _run_cli(
        ["--json", "--dry-run", "--username", "ghost", "--config", "nonexistent.yaml"],
        extra_env=env,
    )
    assert rc == 1
    payload = json.loads(out)
    assert payload["status"] == "error"
    assert payload["error"] == "no_repositories"


def test_non_json_mode_does_not_emit_json():
    """Without --json, stdout is human-facing; parsing as JSON should fail."""
    rc, out, err = _run_cli(["--config", "nonexistent.yaml"])
    # No username → exits 1 with human-friendly message, not JSON
    assert rc == 1
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
