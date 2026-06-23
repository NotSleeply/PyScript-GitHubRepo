"""Unit tests for src.log setup (also reachable via the src.logger shim).

The previous version of these tests hit two Windows-specific issues:
- A module-level `logger = setup_logger()` had already installed a file
  handler pointing at project-root `app.log`, so `os.remove('app.log')`
  in teardown failed with a PermissionError while the handler held it.
- `setup_logger` used an `if not logger.handlers` guard, so calls with
  verbose=True after the first eager init had no effect.

Both are fixed in src.log: setup_logger is idempotent AND responsive to
the verbose flag, and a test fixture below redirects the file handler
to a tmp_path per test, closing it properly on teardown.
"""

import logging
from logging.handlers import RotatingFileHandler

import pytest

from src.log import logger, setup_logger
import src.log as log_module


@pytest.fixture
def isolated_logger(tmp_path, monkeypatch):
    """Rebuild the root RepoDownloader logger pointing at a temp file,
    close all handlers on teardown so the tmp_path can be deleted on
    Windows."""
    monkeypatch.setattr(log_module, "_LOG_FILE", str(tmp_path / "app.log"))

    root = logging.getLogger("RepoDownloader")
    saved = list(root.handlers)
    root.handlers.clear()

    yield setup_logger

    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
    root.handlers.extend(saved)


class TestLoggerInitialization:
    def test_logger_returns_logger_instance(self, isolated_logger):
        assert isinstance(isolated_logger(), logging.Logger)

    def test_logger_name_is_correct(self, isolated_logger):
        assert isolated_logger().name == "RepoDownloader"

    def test_global_logger_accessible(self):
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_logger_level_default(self, isolated_logger):
        assert isolated_logger(verbose=False).level == logging.INFO

    def test_logger_level_verbose(self, isolated_logger):
        """Regression: old singleton guard meant verbose=True was ignored
        after the eager module-level init."""
        assert isolated_logger(verbose=True).level == logging.DEBUG

    def test_level_toggles_on_repeat_call(self, isolated_logger):
        """setup_logger must respond to the current verbose flag, not
        freeze whatever was first passed."""
        assert isolated_logger(verbose=False).level == logging.INFO
        assert isolated_logger(verbose=True).level == logging.DEBUG
        assert isolated_logger(verbose=False).level == logging.INFO


class TestLogFileHandling:
    def test_log_file_created_on_first_message(self, isolated_logger, tmp_path):
        log_path = tmp_path / "app.log"
        fresh = isolated_logger(verbose=False)
        fresh.info("Test message")
        for h in fresh.handlers:
            h.flush()
        assert log_path.exists()

    def test_log_file_contains_message(self, isolated_logger, tmp_path):
        log_path = tmp_path / "app.log"
        fresh = isolated_logger(verbose=False)
        fresh.info("Test log message content")
        for h in fresh.handlers:
            h.flush()
        assert "Test log message content" in log_path.read_text(encoding='utf-8')

    def test_log_format_includes_timestamp(self, isolated_logger, tmp_path):
        log_path = tmp_path / "app.log"
        fresh = isolated_logger(verbose=False)
        fresh.info("Timestamp test")
        for h in fresh.handlers:
            h.flush()
        line = log_path.read_text(encoding='utf-8').splitlines()[0]
        parts = line.split('|')
        assert len(parts) >= 3
        timestamp_part = parts[0].strip()
        assert '20' in timestamp_part


class TestLogRotation:
    def test_rotating_handler_configured(self, isolated_logger):
        fresh = isolated_logger()
        assert any(isinstance(h, RotatingFileHandler) for h in fresh.handlers)

    def test_max_bytes_setting(self, isolated_logger):
        fresh = isolated_logger()
        rh = next(h for h in fresh.handlers if isinstance(h, RotatingFileHandler))
        assert rh.maxBytes == 10 * 1024 * 1024

    def test_backup_count_setting(self, isolated_logger):
        fresh = isolated_logger()
        rh = next(h for h in fresh.handlers if isinstance(h, RotatingFileHandler))
        assert rh.backupCount == 5


class TestVerboseMode:
    def test_verbose_adds_console_handler(self, isolated_logger):
        fresh = isolated_logger(verbose=True)
        console_handlers = [
            h for h in fresh.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) > 0

    def test_debug_messages_do_not_raise(self, isolated_logger):
        fresh = isolated_logger(verbose=True)
        fresh.debug("Debug message in verbose mode")


class TestLogLevels:
    def test_info_level_logging(self, isolated_logger):
        isolated_logger().info("Info message")

    def test_warning_level_logging(self, isolated_logger):
        isolated_logger().warning("Warning message")

    def test_error_level_logging(self, isolated_logger):
        isolated_logger().error("Error message")


class TestLoggerSingletonBehavior:
    def test_multiple_calls_return_same_logger(self, isolated_logger):
        l1 = isolated_logger(verbose=False)
        l2 = isolated_logger(verbose=False)
        assert l1 is l2

    def test_no_duplicate_file_handlers(self, isolated_logger):
        fresh = isolated_logger(verbose=False)
        before = sum(1 for h in fresh.handlers if isinstance(h, RotatingFileHandler))
        isolated_logger(verbose=False)
        isolated_logger(verbose=False)
        after = sum(1 for h in fresh.handlers if isinstance(h, RotatingFileHandler))
        assert after == before