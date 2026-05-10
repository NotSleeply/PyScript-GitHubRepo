"""Backward-compatibility shim. Real implementation lives in src.github.downloader."""

from src.github.downloader import (  # noqa: F401
    NonRetryableError,
    RetryableError,
    _retry_on_retryable,
    clone_git,
    download_zip,
)
