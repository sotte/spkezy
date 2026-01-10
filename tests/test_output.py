import pytest
from spkezy import output

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw_value, expected",
    [
        ("autotype", "autotype"),
        (" AutoType ", "autotype"),
        ("none", "none"),
    ],
)
def test_load_output_config_accepts_supported_post_clipboard_actions(
    monkeypatch, tmp_path, raw_value, expected
):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(f"[output]\npost_clipboard_action = '{raw_value}'\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = output.load_output_config()

    assert config.post_clipboard_action == expected


def test_load_output_config_defaults_to_none_when_config_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = output.load_output_config()

    assert config.post_clipboard_action == "none"


def test_load_output_config_raises_value_error_on_invalid_action(monkeypatch, tmp_path):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text("[output]\npost_clipboard_action = 'invalid'\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    with pytest.raises(ValueError):
        output.load_output_config()


@pytest.mark.parametrize("wayland_value, expected", [("wayland-1", True), (None, False)])
def test_is_wayland_session_reflects_environment_value(monkeypatch, wayland_value, expected):
    if wayland_value is None:
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    else:
        monkeypatch.setenv("WAYLAND_DISPLAY", wayland_value)

    assert output.is_wayland_session() is expected
