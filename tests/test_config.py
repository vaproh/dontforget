from better_dontforget.core.config import Config, describe_secret
from better_dontforget.core.paths import config_dir, data_dir


def test_defaults():
    cfg = Config()
    assert cfg.provider == "gemini"
    assert cfg.notifications_enabled is True
    assert cfg.dark is True
    assert cfg.api_key == ""


def test_set_and_reset(xdg_tmp):
    cfg = Config()
    cfg.set("provider", "openai")
    assert cfg.provider == "openai"
    cfg.set("notifications_enabled", "false")
    assert cfg.notifications_enabled is False
    cfg.set("dark", "false")
    assert cfg.dark is False
    cfg.reset("provider")
    assert cfg.provider == "gemini"
    cfg.reset("dark")
    assert cfg.dark is True


def test_invalid_provider_rejected(xdg_tmp):
    cfg = Config()
    try:
        cfg.set("provider", "bogus")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_save_and_load_roundtrip(xdg_tmp):
    from better_dontforget.core.paths import config_path

    cfg = Config()
    cfg.set("provider", "openai")
    cfg.set("api_key", "secret123")
    cfg.save()
    loaded = Config.load()
    assert loaded.provider == "openai"
    assert loaded.api_key == "secret123"
    # file stored with restrictive permissions
    import os

    mode = os.stat(config_path()).st_mode & 0o777
    assert mode == 0o600


def test_xdg_env_paths(xdg_tmp):
    assert "cfg" in str(config_dir())
    assert "data" in str(data_dir())


def test_xdg_fallback_paths(xdg_fallback):
    assert ".config" in str(config_dir())
    assert ".local/share" in str(data_dir())


def test_secret_masking(xdg_tmp):
    cfg = Config()
    assert describe_secret(cfg) == "not set"
    cfg.api_key = "abc"
    assert describe_secret(cfg) == "configured"
