from better_dontforget.core.config import Config
from better_dontforget.core.providers import (
    GeminiProvider,
    NullProvider,
    OpenAICompatProvider,
    ProviderError,
    build_provider,
)


def test_build_provider_null_without_key(xdg_tmp):
    cfg = Config()  # no api_key, provider gemini
    assert isinstance(build_provider(cfg), NullProvider)


def test_build_provider_gemini_with_key(xdg_tmp):
    cfg = Config()
    cfg.api_key = "dummy"
    provider = build_provider(cfg)
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-2.5-flash"


def test_build_provider_groq_with_key(xdg_tmp):
    cfg = Config()
    cfg.provider = "groq"
    cfg.api_key = "dummy"
    provider = build_provider(cfg)
    assert isinstance(provider, OpenAICompatProvider)
    assert provider.base_url == "https://api.groq.com/openai/v1"


def test_groq_default_model(xdg_tmp):
    cfg = Config()
    cfg.provider = "groq"
    assert cfg.effective_model() == "llama-3.1-8b-instant"


def test_gemini_requires_key():
    try:
        GeminiProvider("")
        assert False
    except ProviderError:
        pass


def test_openai_requires_key():
    try:
        OpenAICompatProvider("")
        assert False
    except ProviderError:
        pass


def test_null_provider_raises(xdg_tmp):
    try:
        NullProvider().complete("x")
        assert False
    except ProviderError:
        pass


def test_effective_model_defaults(xdg_tmp):
    cfg = Config()
    cfg.provider = "openai"
    assert cfg.effective_model() == "gpt-4o-mini"
    cfg.model = "custom-model"
    assert cfg.effective_model() == "custom-model"
