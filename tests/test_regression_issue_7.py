"""Regression tests for Issue #7: layered src/ structure and logging.

These pin the directory layout and the back-compat shims so future moves
don't silently break agent consumers, existing tests, or imports inside
the project.
"""

import logging

import pytest


# ---------------------------------------------------------------------------
# Directory / package structure
# ---------------------------------------------------------------------------

def test_layered_packages_importable():
    import src.cli  # noqa: F401
    import src.config  # noqa: F401
    import src.core  # noqa: F401
    import src.github  # noqa: F401
    import src.log  # noqa: F401
    import src.reports  # noqa: F401


def test_back_compat_shims_reexport_symbols():
    """Old flat-module imports should continue to resolve, so existing
    tests, conftest fixtures, and external callers keep working."""
    # src.api → src.github.api
    from src.api import get_repos
    from src.github.api import get_repos as real_get_repos
    assert get_repos is real_get_repos

    # src.downloader → src.github.downloader
    from src.downloader import clone_git, download_zip, RetryableError, NonRetryableError
    from src.github.downloader import (
        clone_git as real_clone,
        download_zip as real_zip,
    )
    assert clone_git is real_clone
    assert download_zip is real_zip
    assert issubclass(RetryableError, Exception)
    assert issubclass(NonRetryableError, Exception)

    # src.history_report → src.reports.*
    from src.history_report import (
        check_disk_space,
        generate_report,
        get_stats_summary,
        load_sync_history,
        save_sync_history,
    )
    assert callable(check_disk_space)
    assert callable(generate_report)
    assert callable(get_stats_summary)
    assert callable(load_sync_history)
    assert callable(save_sync_history)

    # src.logger → src.log
    from src.logger import logger, setup_logger, get_logger
    assert callable(setup_logger)
    assert callable(get_logger)
    assert isinstance(logger, logging.Logger)

    # src.github_repo_downloader → src.cli
    from src.github_repo_downloader import run
    assert callable(run)


def test_src_config_resolves_to_package_not_module():
    """The old src/config.py shim would conflict with src/config/ package.
    We deleted the shim; this test ensures `src.config` resolves to the
    package and exposes the expected symbols."""
    import src.config as cfg

    # Packages have __path__; modules don't
    assert hasattr(cfg, '__path__'), "src.config must be a package"
    assert callable(cfg.load_config)
    assert callable(cfg.parse_and_merge_args)
    assert callable(cfg.validate_config)


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

def test_get_logger_returns_root_when_empty_name():
    from src.log import get_logger

    root = get_logger("")
    assert root.name == "RepoDownloader"


def test_get_logger_prefixes_root_namespace():
    from src.log import get_logger

    child = get_logger("github.api")
    assert child.name == "RepoDownloader.github.api"


def test_get_logger_idempotent():
    from src.log import get_logger

    a = get_logger("downloader")
    b = get_logger("downloader")
    assert a is b


def test_child_logger_inherits_root_level():
    """Children with no explicit level should fall through to the root's
    level. This keeps setup_logger(verbose=...) authoritative."""
    from src.log import get_logger, setup_logger

    setup_logger(verbose=False)
    child = get_logger("github.api")

    # getEffectiveLevel walks up the parent chain
    assert child.getEffectiveLevel() == logging.INFO

    setup_logger(verbose=True)
    assert child.getEffectiveLevel() == logging.DEBUG

    # Restore default
    setup_logger(verbose=False)
