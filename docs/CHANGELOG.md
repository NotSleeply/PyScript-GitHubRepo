# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-10

A broad product push: the CLI is stable, a machine-readable JSON contract
exists, an optional LLM filter is wired in, the code is split into layers,
CI runs on every PR, and docs match reality.

### Fixed

- Three import/typo bugs that made the CLI crash on every startup ([#1](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/1))
- `validate_config` KeyError on partial option dicts (missing `max_workers` / `mode`)
- `setup_logger` singleton swallowed `verbose=True` after the eager module-level init; 4 `test_logger.py` cases now pass ([#7](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/7))
- `test_api.py` / `test_downloader.py` had been hanging since v0.1.0: stale `@patch` targets + broken pagination stubs ([#11](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/11))
- Python 3.11 SyntaxError on nested same-quote f-strings in probes ([#15](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/15))

### Added

- **`--json` output mode**: stdout becomes a single parseable JSON object, stderr carries rich UI + logs. Exit codes 0/1/2 encode success / config-or-empty / partial failure ([#5](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/5))
- **`skill/SKILL.md`**: Claude Agent skill descriptor so other agents can drive this CLI programmatically
- **`--agent-filter`**: natural-language repo filter via Claude; optional `[agent]` extra; default model `claude-haiku-4-5-20251001` ([#9](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/9))
- **Layered `src/` package structure**: `cli/`, `core/`, `github/`, `config/`, `reports/`, `log/`, `agent/`; each layer depends only on layers below ([#7](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/7))
- **`get_logger(name)`** — per-layer child loggers (`RepoDownloader.github.api`, etc.)
- **GitHub Actions CI**: ubuntu + windows × Python 3.11 + 3.12, coverage gate enforced ([#13](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/13))
- 140+ regression tests across 8 files, including subprocess-isolated probes for startup footprint, JSON contract, and SKILL structure

### Changed

- **Startup cost**: `import main` went from +27.9 MB / +536 modules / ~400 ms to **+4.9 MB / +71 modules / ~44 ms** — heavy deps (`requests`, `git`, `rich`, `tenacity`, `yaml`, `anthropic`) are imported only inside the functions that need them ([#3](https://github.com/NotSleeply/PyScript-GitHubRepo/issues/3))
- **Test coverage**: 0% → 71.76%; coverage gate passes honestly for the first time
- `main.py` now calls `src.cli.run` directly (was: shim via `src.github_repo_downloader`)
- `requires-python` raised to `>=3.11` to match CI matrix
- Config validation errors routed to stderr (were stdout — would corrupt JSON mode)
- README / `config.example.yaml` refreshed to document all the above

### Backward compatibility

- Old flat import paths (`src.downloader`, `src.history_report`, `src.logger`, `src.github_repo_downloader`) kept as thin re-export shims. Existing external callers and tests continue to work.

## [Unreleased]

_No changes yet._

## [0.1.0] - 2025-01-XX

### Added
- Initial release of PyScript-GitHubRepo
- Multi-threaded high-speed concurrent downloading via `max_workers` configuration
- Dual mode support: Git Clone (via GitPython) and ZIP extraction
- Powerful conditional filtering:
  - Language-based filtering (`language`)
  - Minimum star count threshold (`min_stars`)
  - Update date filtering (`updated_after`)
  - Maximum repository limit (`max_repos`)
- Smart branch fallback mechanism (`target_ref`) with automatic default branch detection
- Incremental sync & checkpoint strategy via `last_sync.json`
- Retry & fault tolerance mechanism based on Tenacity library
- Automated summary report generation (Markdown & CSV formats)
- Beautiful CLI interface built with Rich library
- CLI argument support to override YAML configuration
- Comprehensive logging system with `app.log`
- Example configuration file (`config.example.yaml`)
- MIT License

### Technical Features
- Modular architecture with separation of concerns:
  - `api.py`: GitHub API interaction layer
  - `config.py`: Configuration parsing and argument merging
  - `downloader.py`: Download logic (Git clone & ZIP extraction)
  - `github_repo_downloader.py`: Main orchestrator with progress tracking
  - `history_report.py`: History tracking and report generation
  - `logger.py`: Logging configuration
- Support for both `uv` package manager and traditional pip installation
- Cross-platform compatibility (Windows, macOS, Linux)

## Version History Summary

| Version | Date | Description |
|---------|------|-------------|
| 0.2.0 | 2026-05 | CLI fixed + lazy imports + JSON mode + SKILL.md + agent filter + layered packages + CI |
| 0.1.0 | 2025-01 | Initial release with core functionality |

---

## Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities

---

<div align="center">
  <strong>For more details, check the <a href="https://github.com/NotSleeply/PyScript-GitHubRepo/releases">Releases</a> page</strong>
</div>
