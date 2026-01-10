import pytest
from spkezy import runtime

pytestmark = pytest.mark.unit


class LogSpy:
    def __init__(self):
        self.warnings: list[tuple[str, dict]] = []

    def warning(self, event: str, **kwargs):
        self.warnings.append((event, kwargs))


def test_get_config_path_uses_xdg_config_home_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    path = runtime.get_config_path()

    assert path == tmp_path / "spkezy" / "config.toml"


def test_get_config_path_falls_back_to_home_config_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(runtime.Path, "home", lambda: tmp_path)

    path = runtime.get_config_path()

    assert path == tmp_path / ".config" / "spkezy" / "config.toml"


def test_get_data_dir_prefers_xdg_data_home_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    path = runtime.get_data_dir()

    assert path == tmp_path / "spkezy"


def test_get_data_dir_falls_back_to_home_local_share(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(runtime.Path, "home", lambda: tmp_path)

    path = runtime.get_data_dir()

    assert path == tmp_path / ".local" / "share" / "spkezy"


def test_get_socket_path_uses_override_when_provided(tmp_path):
    override = tmp_path / "custom.sock"

    path = runtime.get_socket_path(str(override))

    assert path == override


def test_get_socket_path_uses_xdg_runtime_dir_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    path = runtime.get_socket_path()

    assert path == tmp_path / "spkezy-daemon.sock"


def test_get_socket_path_falls_back_to_tmp(monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

    path = runtime.get_socket_path()

    assert path == runtime.Path("/tmp") / "spkezy-daemon.sock"


def test_load_toml_config_returns_empty_when_config_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = runtime.load_toml_config()

    assert config == {}


def test_load_toml_config_reads_valid_toml(monkeypatch, tmp_path):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("[output]\npost_clipboard_action = 'autotype'\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = runtime.load_toml_config()

    assert config["output"]["post_clipboard_action"] == "autotype"


def test_load_toml_config_logs_warning_and_returns_empty_on_parse_error(monkeypatch, tmp_path):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("invalid = [\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    log = LogSpy()

    config = runtime.load_toml_config(log)

    assert config == {}
    assert log.warnings
