# PyScript-GitHubRepo 🚀

[![CI](https://github.com/NotSleeply/PyScript-GitHubRepo/actions/workflows/ci.yml/badge.svg)](https://github.com/NotSleeply/PyScript-GitHubRepo/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/NotSleeply/PyScript-GitHubRepo)](https://github.com/NotSleeply/PyScript-GitHubRepo/issues)
[![GitHub Stars](https://img.shields.io/github/stars/NotSleeply/PyScript-GitHubRepo?style=social)](https://github.com/NotSleeply/PyScript-GitHubRepo/stargazers)

**A CLI to batch-clone or sync every public repository from a GitHub user/org — designed to be driven by humans *and* by other agents.**

Three things make this more than a one-off script:

1. A **machine-readable JSON contract** (`--json`) so other tools can drive it programmatically.
2. A **standard Claude Agent skill** ([`skill/SKILL.md`](./skill/SKILL.md)) so agent runners discover when and how to invoke it.
3. An **optional LLM filter** (`--agent-filter`) that narrows the repo list with a natural-language prompt.

---

## ✨ Features

### Core capabilities

- **🚀 Concurrent downloads** — configurable worker pool (default 5).
- **📦 Dual backend** — `git` mode clones with full history; `zip` mode is faster, auto-extracts, and removes the branch-suffix top-level dir.
- **🔍 Filters** — `--language`, `--min-stars`, `--updated-after`, `--max-repos`, `--exclude`.
- **🔀 Branch fallback** — if `--target-ref` doesn't exist, falls back to the repo's default branch.
- **♻️ Incremental sync** — `last_sync.json` skips repos whose `updated_at` is unchanged.
- **🛡️ Retry & fault tolerance** — tenacity-powered retries on transient errors. All failures recorded in `logs/app.log`.
- **📊 Reports** — markdown / CSV / JSON summary in `./reports/` after every run.

### Built for agents

- **`--json`** — stdout becomes a single parseable JSON object; all UI/logs go to stderr. Exit codes 0/1/2 encode success / config-or-empty / partial failure.
- **`skill/SKILL.md`** — Claude Agent skill descriptor with frontmatter, full schema, error codes, and typical agent workflows.
- **`--agent-filter`** — pass a natural-language prompt; Claude narrows the candidate list. The model only sees public metadata (name, description, language, stars, `updated_at`) — never your token.

### Performance & ergonomics

- **⚡ Lazy imports** — `import main` adds ~5 MB / ~44 ms cold. Heavy deps (`requests`, `git`, `rich`, `tenacity`, `anthropic`) load only when the code path needs them.
- **🎨 Two output modes** — pretty `rich` UI for humans, pure-JSON stream for agents.
- **🪵 Per-layer logs** — child loggers (`RepoDownloader.github.api`, `RepoDownloader.core.processor`, …) make `--verbose` tail-able.

## 🤖 Use as an agent skill

Other agent runners can drive this CLI without humans in the loop. The contract:

1. **Read `skill/SKILL.md`** — frontmatter (`name`, `description`) tells the agent when this skill applies; the body documents arguments, JSON schema, and exit codes.
2. **Always pass `--json`** so stdout is parseable.
3. **Trust exit codes** — `0` success/dry-run, `1` config or no-results, `2` partial failure.
4. **Parse stdout once** — never grep stderr; that's a UX stream.

```bash
# Probe first with --dry-run to confirm the count and size are sensible
out=$(uv run main.py --json --dry-run --username tiangolo --max-repos 5)
echo "$out" | jq '.count, .estimated_size_mb'

# Then run for real
result=$(uv run main.py --json --username tiangolo --max-repos 5)
case $? in
  0) echo "$result" | jq '.stats' ;;
  1) echo "$result" | jq '.error, .message' ;;
  2) echo "$result" | jq '.failed' ;;
esac
```

Full schema (success / partial / dry-run / error shapes) lives in [`skill/SKILL.md`](./skill/SKILL.md).

## 🧠 Agent filter

Narrow the repo list with a natural-language prompt via Claude — useful when the user wants something subjective ("the best CLI tools", "frameworks not apps").

```bash
uv pip install -e '.[agent]'           # install the optional anthropic SDK
export ANTHROPIC_API_KEY=sk-...

uv run main.py \
  --username tiangolo --json \
  --agent-filter "only CLI tools, not web frameworks" \
  --max-repos 5
```

The JSON response gains an `agent_filter` block:

```json
{
  "status": "ok",
  "agent_filter": {
    "prompt": "only CLI tools, not web frameworks",
    "model": "claude-haiku-4-5-20251001",
    "selected_count": 2,
    "total_considered": 5,
    "rationale": "Selected based on descriptions indicating CLI / terminal usage."
  }
}
```

Default model: `claude-haiku-4-5-20251001`. Override with `--agent-model`. Hard cap of 100 candidates per call. Hallucinated names (not in the candidate list) are dropped.

## 📦 JSON contract

```bash
uv run main.py --json --username <target> [filters...]
```

| Code | Meaning |
|---|---|
| `0` | Success or dry-run |
| `1` | Config error, no repos matched, or insufficient disk |
| `2` | Partial failure — `failed[]` lists the repos that didn't make it |

Error codes (in `error` field): `config_invalid`, `username_required`, `no_repositories`, `insufficient_disk_space`, `agent_missing_key`, `agent_sdk_missing`, `agent_invalid_response`. See [`skill/SKILL.md`](./skill/SKILL.md) for the full schema.

## 🚀 Quick Start

### 1. Install

```bash
uv sync                          # runtime deps
uv pip install -e '.[dev]'       # + test tooling (optional)
uv pip install -e '.[agent]'     # + LLM filter (optional)
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml: set github.username and (recommended) github.token
```

A GitHub token avoids the 60/hour unauthenticated rate limit — any classic PAT with `public_repo` is enough.

### 3. Run

```bash
# Human-friendly output with rich progress bars
uv run main.py --username tiangolo --language Python --min-stars 100

# Dry-run to preview without downloading
uv run main.py --username tiangolo --dry-run --max-repos 5

# JSON output for agents / scripts
uv run main.py --username tiangolo --json --max-repos 5
```

## 🔧 CLI reference

CLI flags override YAML. See [`config.example.yaml`](config.example.yaml) for the full YAML shape.

| Flag | Purpose | Default |
|---|---|---|
| `--username` | **Required.** Target user/org. | — |
| `--token` | GitHub PAT (recommended). | from env / config |
| `--mode` | `git` (with history) or `zip` (faster). | `git` |
| `--save-path` | Where to write repos. | `./repos` |
| `--target-ref` | Branch/tag; falls back to default branch on 404. | `main` |
| `--language` / `--min-stars` / `--updated-after` / `--max-repos` / `--exclude` | Traditional filters. | — |
| `--max-workers` | Thread pool size. 3–10 recommended. | `5` |
| `--agent-filter` | LLM filter (needs `[agent]` extra). | off |
| `--agent-model` | Claude model for `--agent-filter`. | `claude-haiku-4-5-20251001` |
| `--report-format` | `markdown` / `csv` / `json`. | `markdown` |
| `--json` | Structured stdout for agents. | off |
| `--dry-run` | Preview, no downloads. | off |
| `--verbose` | Debug-level logging to stderr + `logs/app.log`. | off |

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

Each layer only depends on layers below it: `cli → core → (github, reports) → (config, log)`. Heavy third-party deps are imported lazily so `--help`, `--version`, and pure-JSON error paths stay fast.

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
