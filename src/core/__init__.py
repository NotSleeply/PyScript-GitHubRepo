"""Orchestration layer: wires configuration → API → per-repo processing →
history → reports. Imports from github/ and reports/ layers; callers in
cli/ provide the progress UI."""

from src.core.orchestrator import (
    execute_downloads,
    is_interrupted,
    mark_interrupted,
    mask_token,
    reset_interrupt,
)
from src.core.processor import process_repo

__all__ = [
    "execute_downloads",
    "process_repo",
    "mask_token",
    "is_interrupted",
    "mark_interrupted",
    "reset_interrupt",
]
