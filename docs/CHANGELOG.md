# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- English README with badges, configuration reference table, and complete documentation
- Chinese README (README_CN.md) for international users
- CONTRIBUTING.md contribution guide with coding standards and PR workflow
- Enhanced pyproject.toml metadata (English description, classifiers, keywords)
- GitHub Issue and Pull Request templates
- Project structure documentation

### Changed
- Improved project description for better PyPI visibility
- Added comprehensive configuration reference table
- Enhanced documentation structure following open-source best practices

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
