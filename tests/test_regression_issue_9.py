"""Regression tests for Issue #9: --agent-filter natural-language repo selection.

Hermetic — no real Anthropic calls. We inject a fake `anthropic` module
via sitecustomize + PYTHONPATH and drive it from the test to exercise
success, invalid-response, and key-missing paths.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(args, env_extra=None, timeout=30):
    env = os.environ.copy()
    # Ensure no real key leaks into tests
    env.pop("ANTHROPIC_API_KEY", None)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return r.returncode, r.stdout, r.stderr


def _write_stubs(tmp_path, repos, *, model_reply=None, raise_on_call=False):
    """Write a sitecustomize that stubs both GitHub and anthropic.

    `model_reply` — the text payload the fake Claude client returns. If
    None, returns a `selected=all-names` reply.
    `raise_on_call` — if True, fake `messages.create` raises to test
    error propagation.
    """
    if model_reply is None:
        model_reply = json.dumps({
            "selected": [r["name"] for r in repos],
            "rationale": "All candidates match (test stub).",
        })

    stub = tmp_path / "sitecustomize.py"
    stub.write_text(textwrap.dedent(f"""
        import sys, json
        import types as _types

        _repos = json.loads({json.dumps(repos)!r})

        _fake_gh = _types.ModuleType('src.github.api')
        _fake_gh.get_repos = lambda *a, **kw: _repos
        sys.modules['src.github.api'] = _fake_gh

        _fake_api_shim = _types.ModuleType('src.api')
        _fake_api_shim.get_repos = lambda *a, **kw: _repos
        sys.modules['src.api'] = _fake_api_shim

        # Fake anthropic SDK
        _reply_text = {model_reply!r}
        _raise = {raise_on_call!r}

        class _Block:
            def __init__(self, t): self.type = 'text'; self.text = t
        class _Msg:
            def __init__(self, t): self.content = [_Block(t)]
        class _Messages:
            def create(self, **kw):
                if _raise:
                    raise RuntimeError('simulated API failure')
                return _Msg(_reply_text)
        class _Anthropic:
            def __init__(self, api_key=None): self.api_key = api_key
            @property
            def messages(self): return _Messages()

        _fake_anthropic = _types.ModuleType('anthropic')
        _fake_anthropic.Anthropic = _Anthropic
        sys.modules['anthropic'] = _fake_anthropic
    """), encoding='utf-8')
    return stub


REPOS = [
    {
        "name": "alpha-cli",
        "description": "A CLI helper",
        "language": "Python",
        "stargazers_count": 10,
        "updated_at": "2026-04-01T12:00:00Z",
        "default_branch": "main",
        "size": 100,
        "clone_url": "https://github.com/x/alpha-cli.git",
        "owner": {"login": "x"},
    },
    {
        "name": "beta-web",
        "description": "A web framework",
        "language": "Python",
        "stargazers_count": 20,
        "updated_at": "2026-04-02T12:00:00Z",
        "default_branch": "main",
        "size": 200,
        "clone_url": "https://github.com/x/beta-web.git",
        "owner": {"login": "x"},
    },
    {
        "name": "gamma-tool",
        "description": "Another CLI tool",
        "language": "Go",
        "stargazers_count": 5,
        "updated_at": "2026-04-03T12:00:00Z",
        "default_branch": "main",
        "size": 50,
        "clone_url": "https://github.com/x/gamma-tool.git",
        "owner": {"login": "x"},
    },
]


# ---------------------------------------------------------------------------
# CLI flag surface
# ---------------------------------------------------------------------------

def test_agent_flags_in_help():
    rc, out, _ = _run_cli(["--help"])
    assert rc == 0
    assert "--agent-filter" in out
    assert "--agent-model" in out
    assert "--agent-api-key" in out


# ---------------------------------------------------------------------------
# Happy path: agent filter narrows repos and appears in JSON output
# ---------------------------------------------------------------------------

def test_agent_filter_dry_run_narrows_repos(tmp_path):
    reply = json.dumps({
        "selected": ["alpha-cli", "gamma-tool"],
        "rationale": "Both have CLI in description.",
    })
    _write_stubs(tmp_path, REPOS, model_reply=reply)
    env = {
        "PYTHONPATH": str(tmp_path) + os.pathsep + str(ROOT),
        "ANTHROPIC_API_KEY": "sk-test",
    }

    rc, out, err = _run_cli([
        "--json", "--dry-run", "--username", "x",
        "--agent-filter", "only CLI tools",
        "--config", "nonexistent.yaml",
    ], env_extra=env)
    assert rc == 0, f"stderr: {err}"
    payload = json.loads(out)
    assert payload["status"] == "dry_run"
    assert payload["count"] == 2
    names = [r["name"] for r in payload["repositories"]]
    assert names == ["alpha-cli", "gamma-tool"]

    assert "agent_filter" in payload
    assert payload["agent_filter"]["prompt"] == "only CLI tools"
    assert payload["agent_filter"]["selected_count"] == 2
    assert payload["agent_filter"]["total_considered"] == 3
    assert "CLI" in payload["agent_filter"]["rationale"]


# ---------------------------------------------------------------------------
# Error: API key missing
# ---------------------------------------------------------------------------

def test_agent_missing_key_returns_agent_missing_key(tmp_path):
    _write_stubs(tmp_path, REPOS)
    env = {"PYTHONPATH": str(tmp_path) + os.pathsep + str(ROOT)}
    # No ANTHROPIC_API_KEY in env

    rc, out, _ = _run_cli([
        "--json", "--dry-run", "--username", "x",
        "--agent-filter", "anything",
        "--config", "nonexistent.yaml",
    ], env_extra=env)
    assert rc == 1
    payload = json.loads(out)
    assert payload["status"] == "error"
    assert payload["error"] == "agent_missing_key"


# ---------------------------------------------------------------------------
# Error: model returns invalid JSON
# ---------------------------------------------------------------------------

def test_agent_invalid_response_surfaces_error(tmp_path):
    _write_stubs(tmp_path, REPOS, model_reply="not json at all")
    env = {
        "PYTHONPATH": str(tmp_path) + os.pathsep + str(ROOT),
        "ANTHROPIC_API_KEY": "sk-test",
    }

    rc, out, _ = _run_cli([
        "--json", "--dry-run", "--username", "x",
        "--agent-filter", "whatever",
        "--config", "nonexistent.yaml",
    ], env_extra=env)
    assert rc == 1
    payload = json.loads(out)
    assert payload["status"] == "error"
    assert payload["error"] == "agent_invalid_response"


# ---------------------------------------------------------------------------
# Fenced JSON is also accepted (the model sometimes wraps in ```json ... ```)
# ---------------------------------------------------------------------------

def test_agent_accepts_code_fenced_reply(tmp_path):
    reply = "```json\n" + json.dumps({"selected": ["beta-web"], "rationale": "web"}) + "\n```"
    _write_stubs(tmp_path, REPOS, model_reply=reply)
    env = {
        "PYTHONPATH": str(tmp_path) + os.pathsep + str(ROOT),
        "ANTHROPIC_API_KEY": "sk-test",
    }

    rc, out, _ = _run_cli([
        "--json", "--dry-run", "--username", "x",
        "--agent-filter", "web",
        "--config", "nonexistent.yaml",
    ], env_extra=env)
    assert rc == 0
    payload = json.loads(out)
    assert payload["count"] == 1
    assert payload["repositories"][0]["name"] == "beta-web"


# ---------------------------------------------------------------------------
# No --agent-filter = no agent module loaded (Issue #3 invariant extension)
# ---------------------------------------------------------------------------

def test_agent_module_not_loaded_when_flag_absent():
    """Without --agent-filter, src.agent must NOT be pulled in — keeps
    the cold path tiny and the anthropic SDK truly optional."""
    probe = (
        "import sys, main\n"  # noqa: F401
        "print('loaded=', 'src.agent' in sys.modules)\n"
        "print('anthropic=', 'anthropic' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "loaded= False" in result.stdout
    assert "anthropic= False" in result.stdout


# ---------------------------------------------------------------------------
# Unit-level: select_repositories directly (no subprocess)
# ---------------------------------------------------------------------------

def test_select_repositories_filters_by_names(monkeypatch):
    """Direct unit test: monkeypatch the anthropic import and verify the
    function filters input by the model's `selected` names."""
    import types

    class _Block:
        def __init__(self, t):
            self.type, self.text = 'text', t

    class _Msg:
        def __init__(self, t):
            self.content = [_Block(t)]

    class _Messages:
        def create(self, **kw):
            return _Msg(json.dumps({
                "selected": ["alpha-cli"],
                "rationale": "only cli",
            }))

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _Messages()

    fake_mod = types.ModuleType('anthropic')
    fake_mod.Anthropic = _FakeClient
    monkeypatch.setitem(sys.modules, 'anthropic', fake_mod)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-test')

    from src.agent import select_repositories
    filtered, meta = select_repositories(REPOS, "cli tools only")
    assert [r["name"] for r in filtered] == ["alpha-cli"]
    assert meta["selected_count"] == 1
    assert meta["total_considered"] == 3
    assert meta["prompt"] == "cli tools only"


def test_select_repositories_raises_on_missing_key(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    # Don't patch anthropic — it may or may not be installed; we only reach
    # the import if the key is present, but we want to test the reverse.
    # Ensure anthropic is importable so we don't trip AgentSDKMissing first.
    import types
    fake_mod = types.ModuleType('anthropic')
    fake_mod.Anthropic = lambda **kw: None
    monkeypatch.setitem(sys.modules, 'anthropic', fake_mod)

    from src.agent import AgentKeyMissing, select_repositories

    with pytest.raises(AgentKeyMissing):
        select_repositories(REPOS, "anything")


def test_select_repositories_drops_hallucinated_names(monkeypatch):
    """Model returning a name that wasn't in the candidate list must be
    dropped — the function must not invent repos it doesn't have data for."""
    import types

    class _Block:
        def __init__(self, t):
            self.type, self.text = 'text', t

    class _Msg:
        def __init__(self, t):
            self.content = [_Block(t)]

    class _Messages:
        def create(self, **kw):
            return _Msg(json.dumps({
                "selected": ["alpha-cli", "does-not-exist", "hallucinated"],
                "rationale": "with hallucinations",
            }))

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _Messages()

    fake_mod = types.ModuleType('anthropic')
    fake_mod.Anthropic = _FakeClient
    monkeypatch.setitem(sys.modules, 'anthropic', fake_mod)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-test')

    from src.agent import select_repositories
    filtered, meta = select_repositories(REPOS, "x")
    assert [r["name"] for r in filtered] == ["alpha-cli"]
    assert meta["selected_count"] == 1
