"""Unit tests for src.core.processor.process_repo.

Covers the four status paths (skip / success / failed / interrupted) with
in-memory fakes for progress and the git/zip backends. No network, no
threads — pure dispatch logic.
"""

import threading
from unittest.mock import MagicMock

import pytest

from src.core.processor import process_repo


class _FakeProgress:
    def __init__(self):
        self.updates = []
        self.advances = 0
        self._next_id = 0

    def add_task(self, description, **kwargs):
        tid = self._next_id
        self._next_id += 1
        return tid

    def update(self, task_id, **kwargs):
        self.updates.append((task_id, kwargs))

    def advance(self, task_id, amount=1):
        self.advances += 1


def _repo(name="repo", updated_at="2026-04-01T12:00:00Z"):
    return {
        "name": name,
        "updated_at": updated_at,
        "default_branch": "main",
        "clone_url": f"https://github.com/x/{name}.git",
        "owner": {"login": "x"},
    }


def _opts(mode="git"):
    return {
        "mode": mode,
        "save_path": "./repos",
        "token": None,
        "target_ref": "main",
        "keep_zip": False,
    }


def _new_stats():
    return {"success": 0, "failed": 0, "skipped": 0}


def test_interrupted_before_work_starts_returns_last_known_updated_at():
    history = {"repo-a": {"updated_at": "2025-01-01T00:00:00Z"}}
    repo = _repo("repo-a")
    stats = _new_stats()
    lock = threading.Lock()
    progress = _FakeProgress()

    result = process_repo(
        repo, _opts(), history, progress, overall_task=0,
        stats=stats, stats_lock=lock,
        interrupt_flag=lambda: True,
    )

    assert result == (repo, "interrupted", "2025-01-01T00:00:00Z")
    assert stats == {"success": 0, "failed": 0, "skipped": 0}
    # No progress churn if we bail early
    assert progress.advances == 0


def test_skipped_when_history_matches_current():
    repo = _repo("repo-a", "2026-04-01T12:00:00Z")
    history = {"repo-a": {"updated_at": "2026-04-01T12:00:00Z"}}
    stats = _new_stats()
    progress = _FakeProgress()

    returned_repo, status, new_updated = process_repo(
        repo, _opts(), history, progress, overall_task=0,
        stats=stats, stats_lock=threading.Lock(),
        interrupt_flag=lambda: False,
    )

    assert returned_repo is repo
    assert status == "skipped"
    assert new_updated == "2026-04-01T12:00:00Z"
    assert stats["skipped"] == 1
    assert stats["success"] == 0
    assert progress.advances == 1


def test_success_path_in_git_mode(monkeypatch):
    called = {}

    def fake_clone_git(repo, opts, progress, task_id):
        called["clone"] = (repo["name"], opts["mode"])
        return "Success"

    def fake_download_zip(*a, **kw):
        raise AssertionError("zip path must not run in git mode")

    monkeypatch.setattr("src.core.processor.clone_git", fake_clone_git)
    monkeypatch.setattr("src.core.processor.download_zip", fake_download_zip)

    repo = _repo("repo-a")
    stats = _new_stats()
    progress = _FakeProgress()

    _, status, new_updated = process_repo(
        repo, _opts(mode="git"), history={}, progress=progress,
        overall_task=0, stats=stats,
        stats_lock=threading.Lock(),
        interrupt_flag=lambda: False,
    )

    assert status == "success"
    assert new_updated == repo["updated_at"]
    assert stats["success"] == 1
    assert called["clone"] == ("repo-a", "git")
    assert progress.advances == 1


def test_success_path_in_zip_mode(monkeypatch):
    called = {}

    monkeypatch.setattr(
        "src.core.processor.download_zip",
        lambda r, o, p, t: called.setdefault("zip", r["name"]) or "Success",
    )
    monkeypatch.setattr(
        "src.core.processor.clone_git",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("git path must not run in zip mode")),
    )

    stats = _new_stats()
    _, status, _ = process_repo(
        _repo("repo-b"), _opts(mode="zip"), history={},
        progress=_FakeProgress(), overall_task=0,
        stats=stats, stats_lock=threading.Lock(),
        interrupt_flag=lambda: False,
    )

    assert status == "success"
    assert stats["success"] == 1
    assert called["zip"] == "repo-b"


def test_failure_path_keeps_last_known_updated_at(monkeypatch):
    """A failed download must not advance the history timestamp —
    otherwise a subsequent skip would mask the failure."""
    def boom(*a, **kw):
        raise RuntimeError("simulated clone failure")

    monkeypatch.setattr("src.core.processor.clone_git", boom)

    history = {"repo-c": {"updated_at": "2025-01-01T00:00:00Z"}}
    repo = _repo("repo-c", "2026-04-01T12:00:00Z")
    stats = _new_stats()

    _, status, new_updated = process_repo(
        repo, _opts(), history, progress=_FakeProgress(),
        overall_task=0, stats=stats,
        stats_lock=threading.Lock(),
        interrupt_flag=lambda: False,
    )

    assert status == "failed"
    assert new_updated == "2025-01-01T00:00:00Z"
    assert stats["failed"] == 1
    assert stats["success"] == 0


def test_failure_on_fresh_repo_returns_none_updated_at(monkeypatch):
    """If history had no entry for the repo, failure returns None."""
    def boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.core.processor.clone_git", boom)

    stats = _new_stats()
    _, status, new_updated = process_repo(
        _repo("newbie"), _opts(), history={},
        progress=_FakeProgress(), overall_task=0,
        stats=stats, stats_lock=threading.Lock(),
        interrupt_flag=lambda: False,
    )

    assert status == "failed"
    assert new_updated is None
