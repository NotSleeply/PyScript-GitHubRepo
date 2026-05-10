# PyScript-GitHubRepo 🚀

[![CI](https://github.com/NotSleeply/PyScript-GitHubRepo/actions/workflows/ci.yml/badge.svg)](https://github.com/NotSleeply/PyScript-GitHubRepo/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/NotSleeply/PyScript-GitHubRepo)](https://github.com/NotSleeply/PyScript-GitHubRepo/issues)
[![GitHub Stars](https://img.shields.io/github/stars/NotSleeply/PyScript-GitHubRepo?style=social)](https://github.com/NotSleeply/PyScript-GitHubRepo/stargazers)

**Batch-clone or sync every public repository of a GitHub user/org from the command line — and from other agents.**

A CLI-first Python tool with structured JSON output, an optional LLM-driven filter, and a [SKILL.md](./skill/SKILL.md) so other Claude Agent–style runners can drive it programmatically.

---

## ✨ Key Features

- **🚀 Concurrent downloads** — configurable worker pool (default 5) pulls many repos in parallel.
- **📦 Dual backend** — `git` mode clones with history via GitPython; `zip` mode is faster, auto-extracts, and removes the branch-suffix top-level dir.
- **🔍 Filters** — `--language`, `--min-stars`, `--updated-after`, `--max-repos`, `--exclude`.
- **🤖 Optional LLM filter (`--agent-filter`)** — describe what you want in plain language, Claude narrows the list. See [🧠 Agent filter](#-agent-filter).
- **🔀 Branch fallback** — if `--target-ref` doesn't exist, auto-falls back to the repo's default branch.
- **♻️ Incremental sync** — `last_sync.json` in the target dir skips repos whose `updated_at` is unchanged.
- **🛡️ Retry & fault tolerance** — tenacity-powered retries on transient errors; all failures logged to `app.log`.
- **📊 Reports** — markdown / CSV / JSON summary of every run in `./reports/`.
- **🎨 Two output modes** — pretty `rich` UI for humans, pure-JSON stream for agents (`--json`).
- **⚡ Lazy imports** — `import main` adds ~4 MB RSS / 44 ms cold. Heavy deps (`requests`, `git`, `rich`, `tenacity`, `anthropic`) are loaded only when the code path needs them.

## 🚀 Quick Start

### 1. Install

```bash
uv sync                          # install runtime deps
uv pip install -e '.[dev]'       # + test tooling
uv pip install -e '.[agent]'     # + the LLM filter (optional)
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml: set github.username and (recommended) github.token
```

A GitHub token avoids the 60/hour unauthenticated rate limit — any classic PAT with the `public_repo` scope is enough.

### 3. Run

```bash
# Human-friendly output with rich progress bars
uv run main.py --username tiangolo --language Python --min-stars 100

# Dry-run to preview without downloading
uv run main.py --username tiangolo --dry-run --max-repos 5

# JSON output for agents / scripts
uv run main.py --username tiangolo --json --max-repos 5
```

## 🤖 JSON mode

Add `--json` and `stdout` becomes a single parseable JSON object. All rich UI / progress / warnings go to `stderr`. Exit codes:

| Code | Meaning |
|---|---|
| `0` | Success, or dry-run completed |
| `1` | Config error, no repos matched, or insufficient disk space |
| `2` | At least one repo failed (see `failed[]`) |

Full schema and error codes are documented in [`skill/SKILL.md`](./skill/SKILL.md). Typical agent usage:

```bash
out=$(uv run main.py --username tiangolo --json --max-repos 3)
echo "$out" | jq '.stats'
echo "$out" | jq -r '.failed[]'
```

## 🧠 Agent filter

Narrow the repo list with a natural-language prompt via Claude. Install the optional extra first:

```bash
uv pip install -e '.[agent]'
export ANTHROPIC_API_KEY=sk-...
```

Then:

```bash
uv run main.py --username tiangolo --json --agent-filter "only CLI tools, not web frameworks"
```

The LLM sees only public metadata (name, description, language, stars, `updated_at`) — never your token. The JSON response gains an `agent_filter` field with prompt, model, rationale, and counts. Default model: `claude-haiku-4-5-20251001` (override with `--agent-model`).

## 🔌 Use as a skill from another agent

[`skill/SKILL.md`](./skill/SKILL.md) is a standard Claude Agent skill descriptor — drop the repo into a plugin path, another agent reads the frontmatter, and it knows when and how to invoke this tool. The contract is: always pass `--json`, read exit codes, parse stdout.

## 🔧 Configuration

CLI flags override YAML. See [`config.example.yaml`](config.example.yaml) for the full shape. Commonly used:

| Flag | Purpose | Default |
|---|---|---|
| `--username` | Required. Target user/org. | — |
| `--token` | GitHub PAT. Strongly recommended. | from env |
| `--mode` | `git` (with history) or `zip` (faster). | `git` |
| `--save-path` | Where to write repos. | `./repos` |
| `--target-ref` | Branch/tag; falls back to default branch on 404. | `main` |
| `--language` / `--min-stars` / `--updated-after` / `--max-repos` / `--exclude` | Traditional filters. | — |
| `--agent-filter` | LLM filter (optional extra). | off |
| `--max-workers` | Thread pool size. 3–10 recommended. | `5` |
| `--report-format` | `markdown` / `csv` / `json`. | `markdown` |
| `--json` | Structured stdout for agents. | off |
| `--dry-run` | Preview, no downloads. | off |
| `--verbose` | Debug-level logging to stderr + `app.log`. | off |

## 🛠️ Architecture

```text
src/
├── cli/          user layer  — argparse, rich UI, --json runner, signal handling
├── core/         orchestration — ThreadPoolExecutor, per-repo processor
├── github/       integration — REST API client + git/zip backends
├── config/       configuration — YAML + CLI + validator
├── reports/      output — history, markdown/csv/json reports, disk preflight
├── log/          logging — idempotent setup + per-layer child loggers
└── agent/        optional — LLM-driven filter (needs `anthropic` extra)
```

Each layer only depends on layers below it: `cli → core → (github, reports) → (config, log)`. Heavy third-party deps are imported lazily so that `--help`, `--version`, and pure-JSON error paths stay fast.

Old flat paths (`src.api`, `src.downloader`, `src.history_report`, `src.logger`, `src.github_repo_downloader`) still work as re-export shims for backward compatibility.

## 🧪 Tests

```bash
uv run pytest                            # 157 tests, 72% coverage
uv run pytest -k issue_                  # regression suite only
uv run pytest --cov=src --cov-report=term
```

CI runs on `ubuntu-latest` × `windows-latest` with Python `3.11` / `3.12` on every PR.

## 🤝 Contributing

See [CONTRIBUTING.md](./docs/CONTRIBUTING.md). Every PR should come with a regression test that fails before the fix and passes after.

## 📝 Changelog

See [CHANGELOG.md](./docs/CHANGELOG.md).

## ⚠️ Disclaimer

Educational and research use only. You are responsible for complying with GitHub's Terms of Service and the licenses of the repositories you download.

## 📄 License

MIT — see [LICENSE](LICENSE).

## 💬 Support

- 📖 **Docs**: this file + [中文文档](./docs/README_CN.md) + [`skill/SKILL.md`](./skill/SKILL.md) (agent contract)
- 🐛 **Bugs**: [Open an issue](https://github.com/NotSleeply/PyScript-GitHubRepo/issues)
- ⭐ **Star** the project if it saves you time

---

<div align="center">
  <strong>Made with ❤️ by NotSleeply</strong>
</div>
