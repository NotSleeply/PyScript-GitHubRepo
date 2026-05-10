# PyScript-GitHubRepo 🚀

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/NotSleeply/PyScript-GitHubRepo)](https://github.com/NotSleeply/PyScript-GitHubRepo/issues)
[![GitHub Stars](https://img.shields.io/github/stars/NotSleeply/PyScript-GitHubRepo?style=social)](https://github.com/NotSleeply/PyScript-GitHubRepo/stargazers)

**A modern, high-performance, and robust Python tool for batch downloading or synchronizing all open-source repositories from any GitHub user via the GitHub API.**

Completely refactored from slow and error-prone browser automation (Selenium) to a fully modular architecture, providing you with a seamless cloning and backup experience.

---

## ✨ Key Features

- **🚀 Multi-threaded High-Speed Concurrency**: Built-in multi-threading support (via `max_workers` config), enabling massive repository cloning/downloading at lightning speed - no more waiting in queue!
- **📦 Dual Mode Support: Git Clone & ZIP Extraction**
  - **Git Mode**: Uses `GitPython` to automatically trigger `git pull` if the repo exists locally, otherwise performs `git clone`, perfectly preserving commit history and Git records.
  - **ZIP Mode**: Rapidly fetches packaged Zip source files via API with **automatic extraction**, auto-cleans branch suffix directories (e.g., `repo-main`), giving you clean project names.
- **🔍 Powerful Conditional Filtering**:
  - `language`: Download only projects in specified programming languages (e.g., `Python`, `JavaScript`)
  - `min_stars`: Set minimum star threshold to filter out low-quality repos
  - `updated_after`: Only download active repositories updated after a specific date
  - `max_repos`: Limit maximum number of operations to save bandwidth
- **🔀 Smart Branch Fallback**: Set any desired target branch via `target_ref`. If that branch (or Tag) doesn't exist, the system automatically queries its real **default branch** and seamlessly falls back, greatly reducing 404/Branch Not Found errors!
- **♻️ Incremental Sync & Checkpoint Strategy**: Automatically records update timestamps via `last_sync.json` in the target directory. If no new changes exist, the tool skips processing to conserve resources.
- **🛡️ Retry & Fault Tolerance Mechanism**: Exponential retry logic based on `Tenacity`. Automatically handles network fluctuations, 502 errors, logs critical fatal errors to `app.log`, preventing a single bad repository from crashing the entire process.
- **📊 Automated Summary Reports**: Generates Markdown or CSV format summary reports in the target directory (default `./reports`) upon download completion.
- **🎨 Beautiful CLI Interface**: Dynamic progress bar built with `Rich`, providing clear visibility into multi-task execution status - say goodbye to log flooding!

## 📸 Demo (Coming Soon)

<!-- Add screenshot or GIF here -->

## 🚀 Quick Start

### 1. Install Dependencies

Use `uv` for ultra-fast virtual environment setup and dependency installation:

```bash
uv sync
```

### 2. Prepare Configuration (Critical!)

When cloning or pulling large-scale content, it's very easy to trigger GitHub's unauthenticated rate limit. We need to provide a Token first:

1. Visit your GitHub Token generation page: [Generate new token (classic)](https://github.com/settings/tokens)
2. No complex permissions needed (if only downloading public repos). Generate and copy your Token starting with `ghp_`.
3. Copy the example configuration file:

```bash
cp config.example.yaml config.yaml
```

Modify `config.yaml` with your information:

```yaml
github:
  username: "codewithsadee"  # GitHub username whose repos you want to download
  token: "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXX"  # Your Token to avoid rate limiting

download:
  mode: "git"            # "zip" or "git"
  save_path: "./repos"   # Directory to save repositories
  target_ref: "main"     # Default branch or Tag to pull
```

### 3. Run the Tool

Execute directly through the entry file:

```bash
uv run main.py
```

You can also use **CLI arguments** to temporarily override any YAML configuration:

```bash
# Download only the latest 3 Python-related starred repos:
uv run main.py --username tiangolo --language Python --min-stars 50 --max-repos 3 --mode git
```

After execution, the system will output a beautiful summary report! You can also view the auto-generated `.md` document report in the directory!

## 🔧 Configuration Reference

See [config.example.yaml](config.example.yaml) for all available options:

| Section | Option | Description | Default |
|---------|--------|-------------|---------|
| **github** | `username` | Target GitHub username | Required |
| | `token` | GitHub personal access token (optional but recommended) | None |
| **download** | `mode` | Download mode: `"git"` or `"zip"` | `"git"` |
| | `save_path` | Directory to save repositories | `"./repos"` |
| | `target_ref` | Branch or tag to checkout | `"master"` |
| | `keep_zip` | Keep zip file after extraction (ZIP mode only) | `false` |
| **filter** | `language` | Filter by programming language | `""` (all) |
| | `min_stars` | Minimum star count threshold | `0` |
| | `updated_after` | Only include repos updated after date (YYYY-MM-DD) | `""` |
| | `max_repos` | Maximum number of repos to process | `0` (unlimited) |
| **concurrency** | `max_workers` | Number of concurrent threads | `5` |
| **report** | `format` | Report format: `"markdown"` or `"csv"` | `"markdown"` |

## 🛠️ Development

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
├── drivers/                      # Browser drivers (legacy)
├── main.py                       # Entry point
├── config.example.yaml           # Example configuration
├── pyproject.toml                # Project metadata & dependencies
└── requirements.txt              # Dependencies list
```

### Running Tests

```bash
# Add test commands here when tests are implemented
```

## 🤝 Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](./docs/CONTRIBUTING.md) guide for details on:

- Code of Conduct
- How to submit Pull Requests
- Coding standards
- Reporting bugs

## 📝 Changelog

View the [CHANGELOG.md](./docs/CHANGELOG.md) for version history and updates.

## ⚠️ Disclaimer

This tool is intended for **educational and research purposes only**. Users assume full responsibility and risk for using this tool. Please adhere to the following principles:

- Comply with GitHub's Terms of Service and rate limits
- Respect the intellectual property rights and licenses of open source project authors
- Do not use downloaded code for commercial purposes (unless explicitly allowed by the original project license)
- The developer is not responsible for any issues or losses resulting from the use of this tool

By using this tool, you agree to the above disclaimer. If you do not agree, please do not use this tool.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [GitPython](https://gitpython.readthedocs.io/) - For Git operations
- [Rich](https://rich.readthedocs.io/) - For beautiful terminal output
- [Tenacity](https://tenacity.readthedocs.io/) - For retry logic
- [PyYAML](https://pyyaml.org/) - For YAML configuration parsing

## 💬 Support

- 📖 **Documentation**: Check this README and [中文文档](./docs/README_CN.md)
- 🐛 **Bug Reports**: [Open an Issue](https://github.com/NotSleeply/PyScript-GitHubRepo/issues)
- 💡 **Feature Requests**: [Start a Discussion](https://github.com/NotSleeply/PyScript-GitHubRepo/discussions)
- ⭐ **Star this project** if you find it helpful!

---

<div align="center">
  <strong>Made with ❤️ by NotSleeply</strong>
</div>
