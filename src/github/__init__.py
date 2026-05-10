"""GitHub integration layer: listing repos via API and materializing them
to disk (git clone or zip download). Nothing here should know about rich
UI, config sources, or reporting — it returns raw data structures and
raises typed exceptions.
"""

from src.github.api import get_repos
from src.github.downloader import (
    NonRetryableError,
    RetryableError,
    clone_git,
    download_zip,
)

__all__ = [
    "get_repos",
    "clone_git",
    "download_zip",
    "RetryableError",
    "NonRetryableError",
]
