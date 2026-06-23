# Agent & Skill Integration Examples

This document shows how other agent tools and Python programs can call
PyScript-GitHubRepo via the CLI + JSON integration path.

The CLI exercises the core pipeline
(`config → github.api → core → reports`), and emits structured JSON
on stdout when invoked with `--json`.

---

## CLI + JSON

### Dry-run preview

Always start with `--dry-run` to confirm the filter matches intent before
committing to a real download.

```bash
uv run main.py --json --dry-run \
  --username octocat \
  --language Python \
  --min-stars 50 \
  --token "$GITHUB_TOKEN"
```

stdout (exactly one JSON object):

```json
{
  "status": "dry_run",
  "username": "octocat",
  "mode": "git",
  "count": 3,
  "estimated_size_mb": 12.34,
  "save_path": "/abs/path/to/repos",
  "repositories": [
    { "name": "...", "language": "Python", "stars": 120, "updated_at": "...", "size_kb": 1024, "description": "..." }
  ]
}
```

### Real download

```bash
uv run main.py --json \
  --username octocat \
  --language Python \
  --min-stars 50 \
  --max-repos 3 \
  --mode git \
  --save-path ./repos \
  --token "$GITHUB_TOKEN"
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | All downloads succeeded |
| 1 | Config error, no repos matched, or insufficient disk |
| 2 | Partial failure — see `failed` array in JSON |

### LLM-driven narrowing (`--agent-filter`)

After traditional filters run, an optional Claude pass can narrow the list
by natural-language intent. Requires `uv pip install anthropic` and
`ANTHROPIC_API_KEY`.

```bash
uv run main.py --json \
  --username tiangolo \
  --min-stars 100 \
  --agent-filter "only the best CLI tools, not web apps" \
  --agent-api-key "$ANTHROPIC_API_KEY" \
  --dry-run
```

The JSON gains an `agent_filter` field with the model's rationale:

```json
{
  "status": "dry_run",
  "agent_filter": {
    "prompt": "only the best CLI tools, not web apps",
    "model": "claude-haiku-4-5-20251001",
    "selected_count": 3,
    "total_considered": 12,
    "rationale": "Selected based on descriptions indicating CLI / terminal usage."
  },
  ...
}
```

### Handling partial failure (exit 2)

```bash
uv run main.py --json --username octocat --save-path ./repos --token "$GITHUB_TOKEN"
code=$?
json=$(cat)
```

```python
import json, subprocess, sys

proc = subprocess.run(
    ["uv", "run", "main.py", "--json", "--username", "octocat",
     "--save-path", "./repos", "--token", "ghp_..."],
    capture_output=True, text=True,
)
result = json.loads(proc.stdout)

if proc.returncode == 0:
    print(f"All {result['stats']['success']} repos downloaded.")
elif proc.returncode == 2:
    print(f"Partial: {result['stats']['success']} ok, {len(result['failed'])} failed.")
    print("Failed:", ", ".join(result["failed"]))
    # Re-running is cheap — unchanged repos are skipped via last_sync.json.
else:
    print(f"Error: {result.get('error')} — {result.get('message')}")
    sys.exit(1)
```
