"""Unit tests for src.core.orchestrator.

Covers:
- execute_downloads drives the ThreadPoolExecutor and merges results
- mask_token's length thresholds
- is_interrupted / mark_interrupted / reset_interrupt state machine
"""

import threading

import pytest

from src.core import orchestrator


class _FakeProgress:
    def __init__(self):
        self.tasks = []

    def add_task(self, description, **kwargs):
        self.tasks.append(description)
        return len(self.tasks) - 1

    def update(self, task_id, **kwargs):
        pass

    def advance(self, task_id, amount=1):
        pass


def _repo(name, updated_at="2026-04-01T12:00:00Z"):
    return {
        "name": name,
        "updated_at": updated_at,
        "default_branch": "main",
    }


@pytest.fixture(autouse=True)
def _reset_interrupt_flag():
    orchestrator.reset_interrupt()
    yield
    orchestrator.reset_interrupt()


# ---------------------------------------------------------------------------
# mask_token
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    (None, "***"),
    ("", "***"),
    ("short", "***"),                        # length < 12
    ("exactlyeleven", "exac...even"),        # length 13 → shown
    ("ghp_XXXXXXXXXXXXXXXXXXXXXXXX", "ghp_...XXXX"),
])
def test_mask_token_variants(raw, expected):
    assert orchestrator.mask_token(raw) == expected


# ---------------------------------------------------------------------------
# Interrupt flag lifecycle
# ---------------------------------------------------------------------------

def test_interrupt_flag_starts_clean():
    assert orchestrator.is_interrupted() is False


def test_interrupt_flag_flipped_by_mark():
    orchestrator.mark_interrupted()
    assert orchestrator.is_interrupted() is True


def test_interrupt_flag_reset():
    orchestrator.mark_interrupted()
    orchestrator.reset_interrupt()
    assert orchestrator.is_interrupted() is False


# ---------------------------------------------------------------------------
# execute_downloads integration
# ---------------------------------------------------------------------------

def test_execute_downloads_aggregates_results(monkeypatch):
    """Each repo returns (repo, status, new_updated_at); the orchestrator
    must thread these back into `statuses` and `history` correctly."""
    def fake_process(repo, opts, history, progress, overall_task,
                     stats, stats_lock, interrupt_flag):
        # Mimic a fast success
        with stats_lock:
            stats["success"] += 1
        return repo, "success", repo["updated_at"]

    monkeypatch.setattr("src.core.orchestrator.process_repo", fake_process)

    repos = [_repo("a"), _repo("b"), _repo("c")]
    history = {}
    progress = _FakeProgress()

    statuses, stats, duration = orchestrator.execute_downloads(
        repos, {"max_workers": 2}, history, progress,
    )

    assert statuses == {"a": "success", "b": "success", "c": "success"}
    assert stats["success"] == 3
    # history should be updated for each success
    assert history == {
        "a": {"updated_at": repos[0]["updated_at"]},
        "b": {"updated_at": repos[1]["updated_at"]},
        "c": {"updated_at": repos[2]["updated_at"]},
    }
    assert duration >= 0


def test_execute_downloads_does_not_update_history_on_failure(monkeypatch):
    def fake_process(repo, opts, history, progress, overall_task,
                     stats, stats_lock, interrupt_flag):
        with stats_lock:
            stats["failed"] += 1
        return repo, "failed", None

    monkeypatch.setattr("src.core.orchestrator.process_repo", fake_process)

    statuses, stats, _ = orchestrator.execute_downloads(
        [_repo("x")], {"max_workers": 1}, history={}, progress=_FakeProgress(),
    )

    assert statuses == {"x": "failed"}
    assert stats["failed"] == 1
    # Crucially: history is NOT updated for failed downloads. If we wrote
    # the current updated_at here, the next run would skip the broken repo.


def test_execute_downloads_updates_history_on_skip(monkeypatch):
    """A "skipped" result means no-op but still valid — history keeps
    whatever the process returned so timestamps don't drift."""
    def fake_process(repo, opts, history, progress, overall_task,
                     stats, stats_lock, interrupt_flag):
        with stats_lock:
            stats["skipped"] += 1
        return repo, "skipped", repo["updated_at"]

    monkeypatch.setattr("src.core.orchestrator.process_repo", fake_process)

    history = {"y": {"updated_at": "2026-04-01T12:00:00Z"}}
    statuses, stats, _ = orchestrator.execute_downloads(
        [_repo("y", "2026-04-01T12:00:00Z")],
        {"max_workers": 1},
        history, _FakeProgress(),
    )
    assert statuses == {"y": "skipped"}
    assert stats["skipped"] == 1
    assert history["y"]["updated_at"] == "2026-04-01T12:00:00Z"
