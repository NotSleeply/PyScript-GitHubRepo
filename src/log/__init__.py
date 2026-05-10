"""Application-wide logging setup.

Exports:
- setup_logger(verbose=False) — idempotent; safe to call repeatedly, responds
  to verbose flag changes (adjusts level, adds console handler on first
  verbose call). Returns the root RepoDownloader logger.
- get_logger(name) — returns a child logger under RepoDownloader (e.g.
  "github", "downloader"), so each layer can prefix its log lines.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


_ROOT_NAME = "RepoDownloader"
_LOG_FILE = os.path.join("logs", "app.log")
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _has_handler(logger, handler_cls, predicate=None):
    for h in logger.handlers:
        if isinstance(h, handler_cls) and (predicate is None or predicate(h)):
            return True
    return False


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Configure and return the root application logger.

    Idempotent: calling this multiple times does not stack handlers. Each call
    reflects the current `verbose` flag:
    - Sets level to DEBUG if verbose else INFO.
    - Ensures exactly one RotatingFileHandler on logs/app.log.
    - Adds a StreamHandler(stdout) on the first verbose=True call; the handler
      is left in place on subsequent calls regardless of verbose (removing it
      would confuse long-running callers).
    """
    logger = logging.getLogger(_ROOT_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    if not _has_handler(logger, RotatingFileHandler):
        log_dir = os.path.dirname(_LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
            delay=True,  # open the file on first emit, not at handler construction
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if verbose and not _has_handler(
        logger,
        logging.StreamHandler,
        predicate=lambda h: not isinstance(h, logging.FileHandler),
    ):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

    # Prevent double-logging through the root logger
    logger.propagate = False
    return logger


def get_logger(name: str = "") -> logging.Logger:
    """Return a child logger under the RepoDownloader namespace.

    Child loggers inherit handlers and level from the root RepoDownloader
    logger. Empty name returns the root itself. This is the preferred API
    for new code; module-level `logger` is kept for backward compatibility.
    """
    if not name:
        return logging.getLogger(_ROOT_NAME)
    if name.startswith(_ROOT_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_NAME}.{name}")


# Eager initialization: callers that just `from src.log import logger` get a
# ready-to-use instance. setup_logger is idempotent, so this is safe.
logger = setup_logger()
