"""LLM-driven repository selection.

Takes a list of GitHub repos (as returned by src.github.api.get_repos) and
a natural-language prompt, returns a filtered subset. The LLM sees only
safe metadata (name, description, language, stars, updated_at) — never
the token or any private data.

`anthropic` is imported lazily inside the function so the SDK stays
optional: callers who never use --agent-filter never pay the import cost,
and it's fine if the package isn't installed.
"""

import json
import os

from src.log import get_logger

logger = get_logger("agent.filter")

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_CANDIDATES = 100  # cap to keep the single-turn prompt bounded


class AgentError(Exception):
    """Base class for agent filter errors. Each subclass carries a stable
    `code` that the JSON runner surfaces to agents as the `error` field."""

    code = "agent_error"


class AgentSDKMissing(AgentError):
    code = "agent_sdk_missing"


class AgentKeyMissing(AgentError):
    code = "agent_missing_key"


class AgentInvalidResponse(AgentError):
    code = "agent_invalid_response"


def _build_candidate_payload(repos):
    """Reduce each repo to the fields the model actually needs to decide.

    Excluding URLs, clone info, owner objects, etc. keeps the context
    tight (relevant for Haiku's smaller window) and avoids leaking
    non-public metadata by accident.
    """
    return [
        {
            "name": r.get("name"),
            "description": r.get("description") or "",
            "language": r.get("language") or "unknown",
            "stars": r.get("stargazers_count", 0),
            "updated_at": r.get("updated_at", "")[:10],
        }
        for r in repos[:MAX_CANDIDATES]
    ]


_SYSTEM_PROMPT = """You help a developer pick a subset of GitHub repositories \
that match a user's natural-language request. You will receive:

1. The user's request (one short sentence).
2. A JSON array of candidate repositories, each with name, description, \
language, stars, and updated_at.

Respond with a single JSON object (no prose, no code fences) of this shape:

{
  "selected": ["repo-name-1", "repo-name-2", ...],
  "rationale": "One short sentence explaining why these were chosen."
}

Rules:
- Only include names that appear in the candidates.
- Prefer quality over quantity — if the user asks for "the best N", honor N.
- If nothing fits, return an empty array and say so in the rationale.
- Never invent repos.
"""


def _parse_response_text(text, valid_names):
    """Parse the model's JSON reply. Be forgiving about leading/trailing
    whitespace or accidental code fences, but require the two documented
    fields."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` or ``` ... ```
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AgentInvalidResponse(f"Model did not return valid JSON: {e}") from e

    if not isinstance(payload, dict) or "selected" not in payload:
        raise AgentInvalidResponse("Model response missing required `selected` field")

    raw_selected = payload.get("selected") or []
    if not isinstance(raw_selected, list):
        raise AgentInvalidResponse("`selected` must be a list")

    selected = [name for name in raw_selected if name in valid_names]
    rationale = str(payload.get("rationale", "")).strip() or "No rationale provided."
    return selected, rationale


def select_repositories(repos, prompt, *, model=None, api_key=None):
    """Ask the model which of `repos` match `prompt`. Returns
    (filtered_repos, metadata_dict). Raises AgentError subclass on failure."""
    if not prompt:
        raise AgentError("Empty agent filter prompt")

    try:
        import anthropic  # lazy
    except ImportError as e:
        raise AgentSDKMissing(
            "The `anthropic` package is not installed. Install with: "
            "uv pip install anthropic"
        ) from e

    resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not resolved_key:
        raise AgentKeyMissing(
            "No API key. Pass --agent-api-key or set ANTHROPIC_API_KEY."
        )

    resolved_model = model or DEFAULT_MODEL
    candidates = _build_candidate_payload(repos)
    valid_names = {c["name"] for c in candidates}

    logger.info(
        "agent filter: model=%s candidates=%d prompt=%r",
        resolved_model, len(candidates), prompt[:120],
    )

    client = anthropic.Anthropic(api_key=resolved_key)
    response = client.messages.create(
        model=resolved_model,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"User request: {prompt}\n\n"
                    f"Candidates (JSON):\n{json.dumps(candidates, ensure_ascii=False)}"
                ),
            }
        ],
    )

    # Extract the text block. content is a list of blocks; we asked for JSON
    # only, so typically one text block.
    text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    if not text_blocks:
        raise AgentInvalidResponse("Model response had no text content")

    selected_names, rationale = _parse_response_text("\n".join(text_blocks), valid_names)
    filtered = [r for r in repos if r["name"] in selected_names]

    metadata = {
        "prompt": prompt,
        "model": resolved_model,
        "selected_count": len(filtered),
        "total_considered": len(candidates),
        "rationale": rationale,
    }
    logger.info(
        "agent filter: selected %d/%d — %s",
        len(filtered), len(candidates), rationale[:120],
    )
    return filtered, metadata
