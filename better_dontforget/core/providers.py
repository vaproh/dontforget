"""AI provider abstraction for Better Dontforget.

Two providers are supported behind a small common interface:

* ``gemini``   — Google Gemini (upstream provider, kept as default).
* ``openai``   — OpenAI-compatible APIs (OpenAI, OpenRouter, self-hosted).

A ``NullProvider`` is used when no credentials are available so that capture and
local search keep working without AI.
"""

from __future__ import annotations

import json
from typing import Protocol, cast

from .config import Config


class ProviderError(Exception):
    """Raised when an AI provider call fails."""


class AIProvider(Protocol):
    name: str

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str: ...


def _safe_json(text: str) -> dict[str, object]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Malformed JSON from provider: {exc}") from exc


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ProviderError("Gemini API key is not configured.")
        self.api_key = api_key
        self.model = model
        self._client = None
        self._types = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(api_key=self.api_key)
            self._types = types
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        from google.genai import types

        client = self._get_client()
        if system and json_mode:
            config = types.GenerateContentConfig(
                system_instruction=system, response_mime_type="application/json"
            )
        elif system:
            config = types.GenerateContentConfig(system_instruction=system)
        elif json_mode:
            config = types.GenerateContentConfig(response_mime_type="application/json")
        else:
            config = None
        try:
            resp = client.models.generate_content(model=self.model, contents=prompt, config=config)
        except Exception as exc:  # network/timeout/quota
            raise ProviderError(f"Gemini request failed: {exc}") from exc
        text = getattr(resp, "text", None)
        if not text:
            raise ProviderError("Gemini returned an empty response.")
        return text

    def list_models(self) -> list[str]:
        client = self._get_client()
        try:
            models = client.models.list()
        except Exception as exc:
            raise ProviderError(f"Failed to list Gemini models: {exc}") from exc
        out: list[str] = []
        for m in models:
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" not in actions:
                continue
            name = getattr(m, "name", "") or ""
            if name.startswith("models/"):
                name = name[len("models/") :]
            out.append(name)
        return sorted(out)


class OpenAICompatProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise ProviderError("OpenAI-compatible API key is not configured.")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url or None,
            )
        return self._client

    def list_models(self) -> list[str]:
        client = self._get_client()
        try:
            models = client.models.list()
        except Exception as exc:
            raise ProviderError(f"Failed to list models: {exc}") from exc
        ids = [m.id for m in getattr(models, "data", models)]
        return sorted(ids)

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            if json_mode:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
            else:
                resp = client.chat.completions.create(model=self.model, messages=messages)
        except Exception as exc:
            raise ProviderError(f"OpenAI-compatible request failed: {exc}") from exc
        content = resp.choices[0].message.content
        if not content:
            raise ProviderError("OpenAI-compatible provider returned an empty response.")
        return content


class NullProvider:
    name = "none"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
    ) -> str:
        raise ProviderError(
            "No AI provider is configured. Set an API key via "
            "`better-dontforget config set api_key <key>` (or the relevant "
            "environment variable). Capture and local search still work."
        )


def build_provider(config: Config) -> AIProvider:
    """Return a provider instance, or ``NullProvider`` when credentials are absent."""
    key = config.resolved_api_key()
    if not key:
        return NullProvider()
    try:
        if config.provider == "gemini":
            return GeminiProvider(key, model=config.effective_model())
        if config.provider == "openai":
            return OpenAICompatProvider(
                key, model=config.effective_model(), base_url=config.resolved_base_url()
            )
        if config.provider == "groq":
            return OpenAICompatProvider(
                key,
                model=config.effective_model(),
                base_url=config.resolved_base_url() or "https://api.groq.com/openai/v1",
            )
    except ProviderError:
        return NullProvider()
    return NullProvider()


def list_models(provider: AIProvider) -> list[str]:
    """Return model ids available from the provider.

    Requires credentials; raises ``ProviderError`` for the ``NullProvider`` or
    when the provider call fails (so the CLI can surface a clear message).
    """
    if isinstance(provider, NullProvider):
        raise ProviderError(
            "No AI provider is configured. Set an API key (e.g. via "
            "`config set api_key <key>`) before listing models."
        )
    fn = getattr(provider, "list_models", None)
    if not callable(fn):
        raise ProviderError(
            f"The {getattr(provider, 'name', '?')} provider does not support model listing."
        )
    return cast("list[str]", fn())
