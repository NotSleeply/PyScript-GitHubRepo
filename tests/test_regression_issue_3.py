"""Regression tests for Issue #3: lazy imports to keep startup lean.

If someone adds a top-level `import requests` (or similar) to a module on
the import path of `main`, these tests fail loudly. The bar is intentionally
tight — the whole point of this issue was that heavy dependencies had
crept into the cold path.
"""

import importlib
import subprocess
import sys
from pathlib import Path


HEAVY_PACKAGES = ("requests", "git", "gitdb", "smmap", "tenacity", "rich", "yaml")


def _run_probe(probe_code: str) -> dict:
    """Run probe_code in a fresh Python and return exec globals as dict.

    A subprocess is required because once `requests` is loaded into the
    current interpreter (by an earlier test, pytest plugin, etc.) it stays
    loaded. Only a cold interpreter gives a trustworthy measurement.
    """
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", probe_code],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"probe failed: {result.stderr}"
    out = {}
    for line in result.stdout.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def test_importing_main_does_not_pull_heavy_deps():
    """`python -c 'import main'` must not load requests/git/rich/tenacity/yaml."""
    probe = (
        "import sys\n"
        "import main\n"  # noqa: F401
        "for pkg in ('requests','git','gitdb','smmap','tenacity','rich','yaml'):\n"
        "    print(f'{pkg}={pkg in sys.modules}')\n"
    )
    loaded = _run_probe(probe)
    offenders = [pkg for pkg, present in loaded.items() if present == "True"]
    assert not offenders, (
        f"Heavy packages loaded at import time — they belong inside the "
        f"function that actually uses them: {offenders}"
    )


def test_module_count_after_import_main_under_budget():
    """Startup module count must stay under a reasonable ceiling.

    Before lazy imports this was 603. After, ~138. The budget below leaves
    room for normal growth but fails loudly on regressions.
    """
    probe = (
        "import sys\n"
        "import main\n"  # noqa: F401
        "print(f'count={len(sys.modules)}')\n"
    )
    out = _run_probe(probe)
    count = int(out["count"])
    assert count < 250, (
        f"sys.modules={count} after `import main`. Budget is 250. "
        f"Something heavy was imported at module scope — check new code."
    )


def test_cli_help_does_not_pull_heavy_deps():
    """`python main.py --help` is the coldest possible path and must stay tiny."""
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"--help failed: {result.stderr}"
    assert "usage:" in result.stdout.lower()


def test_config_module_imports_without_yaml():
    """src.config must not require yaml to import — only to load YAML files."""
    probe = (
        "import sys\n"
        "from src import config\n"  # noqa: F401
        "print(f'yaml={'yaml' in sys.modules}')\n"
    )
    out = _run_probe(probe)
    assert out["yaml"] == "False"


def test_api_module_imports_without_requests():
    """src.api must not require requests to import — only to call get_repos."""
    probe = (
        "import sys\n"
        "from src import api\n"  # noqa: F401
        "print(f'requests={'requests' in sys.modules}')\n"
    )
    out = _run_probe(probe)
    assert out["requests"] == "False"


def test_downloader_module_imports_without_git_or_requests():
    """src.downloader must not pull git/requests/tenacity at import time."""
    probe = (
        "import sys\n"
        "from src import downloader\n"  # noqa: F401
        "for pkg in ('git', 'requests', 'tenacity'):\n"
        "    print(f'{pkg}={pkg in sys.modules}')\n"
    )
    out = _run_probe(probe)
    for pkg in ("git", "requests", "tenacity"):
        assert out[pkg] == "False", f"{pkg} leaked into src.downloader import"
