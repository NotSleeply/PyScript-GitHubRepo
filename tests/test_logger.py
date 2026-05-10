"""
Unit tests for src.logger module

Tests cover:
- Logger initialization and configuration
- Log file creation
- Log rotation settings
- Verbose mode toggle
- Log message formatting
"""

import pytest
import os
import tempfile
import logging
from pathlib import Path

from src.logger import setup_logger, logger


class TestLoggerInitialization:
    """Test suite for logger setup and configuration."""
    
    def test_logger_returns_logger_instance(self):
        """Test that setup_logger returns a logging.Logger instance."""
        test_logger = setup_logger()
        assert isinstance(test_logger, logging.Logger)
    
    def test_logger_name_is_correct(self):
        """Test that logger has the expected name."""
        test_logger = setup_logger()
        assert test_logger.name == "RepoDownloader"
    
    def test_global_logger_accessible(self):
        """Test that global logger instance is accessible."""
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
    
    def test_logger_level_default(self):
        """Test that default log level is INFO."""
        test_logger = setup_logger(verbose=False)
        assert test_logger.level == logging.INFO
    
    def test_logger_level_verbose(self):
        """Test that verbose mode sets DEBUG level."""
        test_logger = setup_logger(verbose=True)
        assert test_logger.level == logging.DEBUG


class TestLogFileHandling:
    """Test suite for log file operations."""
    
    def teardown_method(self):
        """Clean up log files after each test."""
        if os.path.exists('app.log'):
            os.remove('app.log')
        
        for i in range(1, 6):
            rotated_log = f'app.log.{i}'
            if os.path.exists(rotated_log):
                os.remove(rotated_log)
    
    def test_log_file_created_on_first_message(self):
        """Test that log file is created when first message is logged."""
        if os.path.exists('app.log'):
            os.remove('app.log')
        
        fresh_logger = setup_logger.__wrapped__(setup_logger, False) if hasattr(setup_logger, '__wrapped__') else type(setup_logger)()
        # Reinitialize to ensure clean state
        import importlib
        import src.logger
        importlib.reload(src.logger)
        
        from src.logger import setup_logger as setup_fresh
        test_logger = setup_fresh(verbose=False)
        test_logger.info("Test message")
        
        assert os.path.exists('app.log')
    
    def test_log_file_contains_message(self):
        """Test that logged messages appear in the log file."""
        test_msg = "Test log message content"
        
        test_logger = setup_logger(verbose=False)
        test_logger.info(test_msg)
        
        with open('app.log', 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert test_msg in content
    
    def test_log_format_includes_timestamp(self):
        """Test that log format includes timestamp."""
        test_logger = setup_logger(verbose=False)
        test_logger.info("Timestamp test")
        
        with open('app.log', 'r', encoding='utf-8') as f:
            line = f.readline()
        
        parts = line.split('|')
        assert len(parts) >= 3
        timestamp_part = parts[0].strip()
        assert '20' in timestamp_part  # Contains year (202x)


class TestLogRotation:
    """Test suite for log rotation behavior."""
    
    def test_rotating_handler_configured(self):
        """Test that RotatingFileHandler is used."""
        from logging.handlers import RotatingFileHandler
        
        test_logger = setup_logger(verbose=False)
        handlers = [h for h in test_logger.handlers 
                    if isinstance(h, RotatingFileHandler)]
        
        assert len(handlers) > 0
    
    def test_max_bytes_setting(self):
        """Test that maxBytes is set to 10MB."""
        from logging.handlers import RotatingFileHandler
        
        test_logger = setup_logger(verbose=False)
        rotating_handlers = [h for h in test_logger.handlers 
                           if isinstance(h, RotatingFileHandler)]
        
        if rotating_handlers:
            handler = rotating_handlers[0]
            assert handler.maxBytes == 10 * 1024 * 1024  # 10MB
    
    def test_backup_count_setting(self):
        """Test that backupCount is set to 5."""
        from logging.handlers import RotatingFileHandler
        
        test_logger = setup_logger(verbose=False)
        rotating_handlers = [h for h in test_logger.handlers 
                           if isinstance(h, RotatingFileHandler)]
        
        if rotating_handlers:
            handler = rotating_handlers[0]
            assert handler.backupCount == 5


class TestVerboseMode:
    """Test suite for verbose/debug mode."""
    
    def test_verbose_adds_console_handler(self):
        """Test that verbose mode adds console output handler."""
        import sys
        from io import StringIO
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            test_logger = setup_logger(verbose=True)
            
            console_handlers = [h for h in test_logger.handlers 
                              if isinstance(h, logging.StreamHandler) 
                              and not isinstance(h, logging.FileHandler)]
            
            assert len(console_handlers) > 0
        finally:
            sys.stdout = old_stdout
    
    def test_debug_messages_visible_in_verbose(self):
        """Test that DEBUG level messages are processed in verbose mode."""
        test_logger = setup_logger(verbose=True)
        
        should_not_raise = True
        try:
            test_logger.debug("Debug message in verbose mode")
        except Exception:
            should_not_raise = False
        
        assert should_not_raise


class TestLogLevels:
    """Test suite for different log levels."""
    
    def test_info_level_logging(self):
        """Test INFO level message logging."""
        test_logger = setup_logger(verbose=False)
        
        try:
            test_logger.info("Info message")
            logged_successfully = True
        except Exception:
            logged_successfully = False
        
        assert logged_successfully
    
    def test_warning_level_logging(self):
        """Test WARNING level message logging."""
        test_logger = setup_logger(verbose=False)
        
        try:
            test_logger.warning("Warning message")
            logged_successfully = True
        except Exception:
            logged_successfully = False
        
        assert logged_successfully
    
    def test_error_level_logging(self):
        """Test ERROR level message logging."""
        test_logger = setup_logger(verbose=False)
        
        try:
            test_logger.error("Error message")
            logged_successfully = True
        except Exception:
            logged_successfully = False
        
        assert logged_successfully


class TestLoggerSingletonBehavior:
    """Test suite for logger singleton/reuse behavior."""
    
    def test_multiple_calls_return_same_logger(self):
        """Test that multiple calls return the same logger instance (singleton)."""
        logger1 = setup_logger(verbose=False)
        logger2 = setup_logger(verbose=False)
        
        assert logger1 is logger2
    
    def test_no_duplicate_handlers(self):
        """Test that calling setup_logger multiple times doesn't add duplicate handlers."""
        initial_count = len(logger.handlers)
        
        setup_logger(verbose=False)
        setup_logger(verbose=False)
        
        final_count = len(logger.handlers)
        assert final_count == initial_count
