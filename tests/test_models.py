from better_dontforget import cli
from better_dontforget.core.config import Config
from better_dontforget.core.providers import ProviderError, list_models


class FakeModelsProvider:
    name = "fake"

    def __init__(self, models):
        self._models = models
        self.called = False

    def list_models(self):
        self.called = True
        return list(self._models)

    def complete(self, prompt, *, system=None, json_mode=False):
        raise NotImplementedError


def test_list_models_returns_ids(xdg_tmp):
    provider = FakeModelsProvider(["gpt-4o", "gpt-4o-mini"])
    assert list_models(provider) == ["gpt-4o", "gpt-4o-mini"]
    assert provider.called


def test_list_models_null_provider_errors(xdg_tmp):
    from better_dontforget.core.providers import NullProvider

    try:
        list_models(NullProvider())
        assert False
    except ProviderError:
        pass


def test_models_command_prints(xdg_tmp, capsys, monkeypatch):
    config = Config()
    monkeypatch.setattr(cli, "build_provider", lambda c: FakeModelsProvider(["a", "b"]))
    monkeypatch.setattr(cli, "_config", lambda: config)
    rc = cli.main(["models"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "a" in out and "b" in out
    assert "config set model" in out


def test_models_command_no_provider(xdg_tmp, capsys, monkeypatch):
    config = Config()
    from better_dontforget.core.providers import NullProvider

    monkeypatch.setattr(cli, "build_provider", lambda c: NullProvider())
    monkeypatch.setattr(cli, "_config", lambda: config)
    rc = cli.main(["models"])
    assert rc == 1
    assert "No AI provider is configured" in capsys.readouterr().out
