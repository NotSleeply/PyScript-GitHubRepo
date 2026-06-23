---
name: github-repo-batch
description: Use when the user wants to batch-clone or sync all public repositories from a GitHub user or organization, with filtering by language/stars/date and automated Markdown/CSV/JSON reports. Emits structured JSON on stdout when invoked with --json, so other agents can consume the result programmatically.
---

# GitHub Repo Batch Skill

This skill drives the `PyScript-GitHubRepo` CLI. It clones or syncs every public repository of a target GitHub user/org in parallel, applies filters (language, stars, date, excludes, max count), writes an incremental sync history, and produces a machine-readable JSON summary.

## When to use

- "Clone all of user X's repos"
- "Download every Python repo with >100 stars from org Y, only those updated since 2025-01-01"
- "Sync my existing local mirror of user Z's repos"
- "Dry-run: just tell me what would be downloaded"

Do NOT use for: fetching a single repo (use plain `git clone`), private repos outside the caller's token scope, or repos from Git hosts other than github.com.

## Prerequisites

1. **Python environment** — this repo uses `uv`. Run `uv sync` once before first use.
2. **GitHub token (recommended)** — unauthenticated requests are capped at 60/hour, which runs out on any real user. Set via `--token <PAT>` or the `github.token` key in `config.yaml`. A `repo` scope is enough for public repos.
3. **Working directory** — invoke from the project root so `main.py` resolves.

## Invocation

### JSON mode (recommended for agents)

```bash
uv run main.py --json --username <target> [filters...] [--dry-run]
```

**Contract:** stdout contains exactly one JSON object followed by a newline. Everything else (progress, warnings, rich UI) is written to stderr — agents should either capture or ignore it. Parse stdout with `json.loads`.

**Exit codes:**

| Code | Meaning                                                                                           |
| ---- | ------------------------------------------------------------------------------------------------- |
| `0`  | All downloads succeeded, or dry-run completed                                                     |
| `1`  | Configuration error, no repositories matched, or insufficient disk space — nothing was downloaded |
| `2`  | At least one repo failed; the JSON's `failed` array lists them                                    |

### Human mode (default)

```bash
uv run main.py --username <target> [filters...]
```

Emits a rich progress UI and a Markdown/CSV summary report. Don't parse its stdout — it isn't stable.

## Arguments

| Flag              | Purpose                                                   | Example                                   |
| ----------------- | --------------------------------------------------------- | ----------------------------------------- |
| `--username`      | **Required.** GitHub user or org to enumerate             | `--username tiangolo`                     |
| `--token`         | GitHub Personal Access Token (strongly recommended)       | `--token ghp_xxx`                         |
| `--mode`          | `git` (clone with history) or `zip` (faster, no history)  | `--mode git`                              |
| `--save-path`     | Where to put repos                                        | `--save-path ./repos`                     |
| `--target-ref`    | Branch or tag to checkout; falls back to default branch   | `--target-ref main`                       |
| `--language`      | Filter by primary language                                | `--language Python`                       |
| `--min-stars`     | Floor on star count                                       | `--min-stars 50`                          |
| `--updated-after` | Only repos updated on/after `YYYY-MM-DD`                  | `--updated-after 2025-01-01`              |
| `--max-repos`     | Cap the number of repos (0 = unlimited)                   | `--max-repos 10`                          |
| `--exclude`       | Space-separated repo names to skip                        | `--exclude foo bar`                       |
| `--max-workers`   | Concurrent threads (recommended 3–10)                     | `--max-workers 5`                         |
| `--dry-run`       | Preview matches, do not download                          | `--dry-run`                               |
| `--json`          | Structured output for agents                              | `--json`                                  |
| `--config`        | Path to YAML config with defaults                         | `--config config.yaml`                    |
| `--agent-filter`  | Natural-language filter via Claude (optional)             | `--agent-filter "best CLI tools"`         |
| `--agent-model`   | Claude model for `--agent-filter`                         | `--agent-model claude-haiku-4-5-20251001` |
| `--agent-api-key` | API key for `--agent-filter` (or `ANTHROPIC_API_KEY` env) |                                           |

CLI flags override the equivalent YAML keys. See `config.example.yaml` for the YAML layout.

## LLM-driven filtering (`--agent-filter`)

Optional feature. After traditional filters (language/stars/date/excludes) run, the remaining repos can be narrowed further with a natural-language prompt. Useful when the user asks for something subjective ("best CLI tools", "frameworks, not apps", "repos that would help learning Rust").

Requirements:

- `uv pip install anthropic` (or install the `agent` extra: `uv pip install -e '.[agent]'`)
- Set `ANTHROPIC_API_KEY` or pass `--agent-api-key`

Behavior:

- The model sees only public metadata — name, description, language, stars, updated_at. Never the token or file content.
- Default model: `claude-haiku-4-5-20251001`. Override with `--agent-model`.
- Hard cap of 100 candidates sent to the model. If traditional filters leave more, narrow them first (e.g. raise `--min-stars`).
- If the model fails or returns invalid JSON, the JSON runner emits `status=error, error=agent_invalid_response` and exits 1.

JSON output gains an `agent_filter` field:

```json
{
  "status": "ok",
  "agent_filter": {
    "prompt": "only CLI tools",
    "model": "claude-haiku-4-5-20251001",
    "selected_count": 3,
    "total_considered": 12,
    "rationale": "Selected based on descriptions indicating CLI / terminal usage."
  },
  ...
}
```

New error codes for agent failures: `agent_missing_key`, `agent_sdk_missing`, `agent_invalid_response`.

## Output schema (JSON mode)

### Success / partial success

```json
{
  "status": "ok", // "ok" | "partial"
  "username": "octocat",
  "mode": "git",
  "save_path": "/abs/path/to/repos",
  "duration_seconds": 3.45,
  "stats": {
    "total": 10,
    "success": 9,
    "failed": 1,
    "skipped": 0,
    "success_rate": 90.0,
    "throughput_per_sec": 2.9
  },
  "repositories": [
    {
      "name": "repo-a",
      "status": "success", // "success" | "failed" | "skipped" | "interrupted"
      "language": "Python",
      "stars": 42,
      "updated_at": "2026-04-01T12:00:00Z",
      "default_branch": "main",
      "size_kb": 1024,
      "local_path": "/abs/path/to/repos/repo-a"
    }
  ],
  "failed": ["repo-x"],
  "report_path": "/abs/path/to/reports/repo_report_20260510_153022.md"
}
```

`status` = `"partial"` whenever `failed` is non-empty. Exit code tracks this too.

### Dry-run

```json
{
  "status": "dry_run",
  "username": "octocat",
  "mode": "git",
  "count": 3,
  "estimated_size_mb": 12.34,
  "save_path": "/abs/path/to/repos",
  "repositories": [
    {
      "name": "...",
      "language": "...",
      "stars": 0,
      "updated_at": "...",
      "size_kb": 0,
      "description": "..."
    }
  ]
}
```

### Error

```json
{ "status": "error", "error": "<code>", "message": "<human text>" }
```

Possible `error` codes: `config_invalid`, `username_required`, `no_repositories`, `insufficient_disk_space`.

## Typical agent workflow

1. **Probe first with `--dry-run`** to confirm the filter targets what the user meant and the count is reasonable. Show the user the `count` and `estimated_size_mb` before committing.
2. **Run for real** without `--dry-run`. Capture stdout, parse as JSON, check exit code.
3. **On exit 2 (partial failure)**, inspect `failed` array. Common causes: branch/tag missing, repo is a submodule reference, network blip. The `logs/app.log` file (relative to where you ran the CLI) has full stack traces.
4. **Re-runs are cheap** — the tool keeps `last_sync.json` in `save_path` and skips repos whose `updated_at` hasn't changed. So the natural retry is just invoking again.

## Example: "Clone octocat's top 3 Python repos"

```bash
uv run main.py --json \
  --username octocat --language Python --min-stars 50 \
  --max-repos 3 --mode git --save-path ./repos \
  --token "$GITHUB_TOKEN"
```

Parse the returned JSON; surface `stats.success / total` to the user and any `failed` names.

## Failure modes to handle

- **Rate limit** (`status: "error"`, repo list empty) — the tool logs `"Rate limit exceeded"` to `logs/app.log` and exits 1. Make sure `--token` is set.
- **User not found** — same shape, `error: "no_repositories"` and `logs/app.log` has `"User not found"`.
- **Branch fallback** — if `--target-ref` doesn't exist, the tool auto-falls back to the repo's `default_branch`. Non-fatal.
- **Partial failure** — exit 2 is the expected signal. The `failed` array is authoritative; don't re-derive from `repositories[].status` unless you want identical data.

## Do not

- Don't parse human-mode output. Always pass `--json`.
- Don't mix `--json` with rich UI flags expecting parseable color codes — `--json` suppresses all rich output on stdout.
- Don't set `--max-workers` above 10 without a token — GitHub will 403 you.
- Don't assume `report_path` is always present; it can be `null` if report generation failed (rare).
