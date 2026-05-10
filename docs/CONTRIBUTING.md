# Contributing to PyScript-GitHubRepo

Thank you for considering contributing to PyScript-GitHubRepo! This document provides guidelines and instructions for contributing to this project.

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [How Can I Contribute?](#-how-can-i-contribute)
- [Reporting Bugs](#-reporting-bugs)
- [Suggesting Enhancements](#-suggesting-enhancements)
- [Pull Requests](#-pull-requests)
- [Coding Standards](#-coding-standards)
- [Development Setup](#-development-setup)

## 🤝 Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. By participating, you are expected to uphold this code:

- **Be respectful**: Treat others with respect and professionalism
- **Be welcoming**: Welcome newcomers and help them get started
- **Be collaborative**: Work together to find the best solutions
- **Be constructive**: Provide constructive feedback and focus on what's best for the community

## 💡 How Can I Contribute?

### Reporting Bugs

Before submitting a bug report:

1. **Check existing issues** to avoid duplicates
2. **Use the latest version** of the software
3. **Collect relevant information**:
   - Operating system and Python version
   - Full error traceback (if applicable)
   - Steps to reproduce the issue
   - Expected vs actual behavior

When reporting bugs, please use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md).

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- Use a clear and descriptive title
- Provide a detailed description of the proposed functionality
- Explain why this enhancement would be useful
- Include examples of how it would work (if applicable)

When suggesting enhancements, please use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).

### Pull Requests

We welcome Pull Requests! Here's how to get started:

1. **Fork the repository** and clone your fork
2. **Create a branch** for your changes: `git checkout -b feature/your-feature-name`
3. **Make your changes** following our [coding standards](#-coding-standards)
4. **Test your changes** thoroughly
5. **Commit your changes** with clear commit messages
6. **Push to your fork** and submit a Pull Request

#### Pull Request Guidelines

- **One PR per feature/fix**: Keep each PR focused on a single issue
- **Follow the template**: Use the [PR template](.github/PULL_REQUEST_TEMPLATE.md) when available
- **Update documentation**: If you change functionality, update README or docstrings
- **Add tests**: Include tests for new features (when applicable)
- **Keep it small**: Smaller PRs are easier to review and merge

## 🐛 Reporting Bugs

### Before Submitting

Please check the following before submitting a bug report:

- ✅ You're using the latest version
- ✅ The issue hasn't already been reported
- ✅ You can reproduce the issue consistently
- ✅ You've collected all necessary information

### Bug Report Template

When submitting a bug report, include:

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., Windows 10, macOS 12, Ubuntu 22.04]
- Python Version: [e.g., 3.10.6]
- Package Version: [e.g., 0.1.0]

**Additional context**
Any other context about the problem.
```

## ✨ Suggesting Enhancements

### Enhancement Request Template

When suggesting enhancements, include:

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Other context or screenshots about the feature.
```

## 🔧 Coding Standards

### Python Style Guide

We follow PEP 8 style guidelines with some modifications:

- **Line length**: Maximum 100 characters (soft limit)
- **Imports**: Group imports in order: standard library, third-party, local
- **Naming conventions**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_leading_underscore`

### Code Quality

- Write clear, readable code with comments where necessary
- Use type hints for function signatures
- Follow DRY (Don't Repeat Yourself) principle
- Keep functions focused and small
- Handle errors gracefully with proper logging

### Commit Messages

Use clear and descriptive commit messages:

```
feat: add support for custom download filters
fix: resolve issue with ZIP extraction on Windows
docs: update installation instructions in README
refactor: improve error handling in API module
test: add unit tests for config parser
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

## 🛠️ Development Setup

### Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- Git

### Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/NotSleeply/PyScript-GitHubRepo.git
   cd PyScript-GitHubRepo
   ```

2. **Set up virtual environment**:
   ```bash
   uv sync
   ```

3. **Activate environment** (if needed):
   ```bash
   uv shell
   ```

4. **Run the tool**:
   ```bash
   uv run main.py --help
   ```

### Project Structure

```
PyScript-GitHubRepo/
├── src/
│   ├── api.py                    # GitHub API interaction
│   ├── config.py                 # Configuration parsing & merging
│   ├── downloader.py             # Git clone & ZIP download logic
│   ├── github_repo_downloader.py # Main orchestrator
│   ├── history_report.py         # History tracking & report generation
│   └── logger.py                 # Logging setup
├── main.py                       # Entry point
├── config.example.yaml           # Example configuration
└── pyproject.toml                # Project metadata & dependencies
```

## 📝 Testing

Currently, we don't have automated tests set up, but we encourage contributors to:

- Test their changes manually
- Verify edge cases are handled
- Ensure backward compatibility
- Document any breaking changes

If you'd like to help implement test coverage, we'd love that! Please open an issue first to discuss the approach.

## ❓ Questions?

If you have questions about contributing:

- Check existing [Issues](https://github.com/NotSleeply/PyScript-GitHubRepo/issues) and [Discussions](https://github.com/NotSleeply/PyScript-GitHubRepo/discussions)
- Open a new Discussion for general questions
- Contact maintainers through issues for specific concerns

## 🙏 Recognition

All contributors will be recognized in the project's CONTRIBUTORS file (to be added). Thank you for making this project better!

---

<div align="center">
  <strong>Happy Contributing! 🎉</strong>
</div>
