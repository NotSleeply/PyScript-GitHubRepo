"""PyScript-GitHubRepo source package.

Layers (bottom → top):
- src.log          — logging setup
- src.config       — YAML + CLI merge + validation
- src.github       — GitHub API client + download backends (git/zip)
- src.reports      — sync history, run reports, disk-space preflight, stats
- src.core         — orchestrator (concurrency) + per-repo processor
- src.agent        — optional LLM-driven repository filter
- src.cli          — argparse entry, human rich UI, JSON runner
"""