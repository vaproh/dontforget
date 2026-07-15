"""High-level AI helpers built on top of the provider abstraction.

These functions wrap provider calls with the prompts used by Better Dontforget
and degrade gracefully: tagging/keyword/synthesis failures do not lose user
input and never raise into the capture or search paths.
"""

from __future__ import annotations

from .models import Note
from .providers import AIProvider, ProviderError, _safe_json

_TAG_PROMPT = (
    "Generate up to 5 concise search tags for the following thought. "
    "Prefer concepts over literal words. "
    'Respond ONLY with JSON: {"tags": ["tag1", "tag2"]}'
)

_KEYWORD_PROMPT = (
    "Extract 3-5 keywords to search a personal memory database for the user's "
    'question. Respond ONLY with JSON: {"keywords": ["word1", "word2"]}'
)


def generate_tags(provider: AIProvider, text: str) -> list[str]:
    try:
        resp = provider.complete(_TAG_PROMPT, json_mode=True)
        data = _safe_json(resp)
        tags = data.get("tags", [])
        if isinstance(tags, list):
            return [str(t).strip() for t in tags if str(t).strip()]
    except ProviderError:
        pass
    return []


def extract_keywords(provider: AIProvider, question: str) -> list[str]:
    try:
        resp = provider.complete(_KEYWORD_PROMPT, json_mode=True)
        data = _safe_json(resp)
        kws = data.get("keywords", [])
        if isinstance(kws, list):
            return [str(k).strip() for k in kws if str(k).strip()]
    except ProviderError:
        pass
    return []


def synthesize(provider: AIProvider, question: str, context: str) -> str:
    today = _today()
    prompt = (
        "You are a Memory Assistant.\n"
        f"Date: {today}\n"
        f'User Query: "{question}"\n\n'
        "Relevant Memories:\n"
        f"{context}\n\n"
        "Task:\n"
        "1. Answer the question using ONLY the memories above.\n"
        "2. If asking for 'today' or 'last week', check the timestamps.\n"
        "3. If no relevant memories found, say 'No relevant info found.'"
    )
    try:
        return provider.complete(prompt)
    except ProviderError as exc:
        raise exc


def format_context(rows: list[Note]) -> str:
    lines = []
    for r in rows:
        lines.append(f"[ID:{r.id}] [{r.timestamp}] {r.display_text}")
    return "\n".join(lines)


def _today() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %A")
