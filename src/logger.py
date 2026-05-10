"""Backward-compatibility shim. Real implementation lives in src.log package."""

from src.log import get_logger, logger, setup_logger  # noqa: F401
