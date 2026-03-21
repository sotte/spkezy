import pytest
from spkezy import audio

pytestmark = pytest.mark.unit


def test_load_audio_config_defaults_to_auto(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = audio.load_audio_config()

    assert config.input_device == "auto"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("auto", "auto"),
        ("default", "default"),
        (" some_source_name ", "some_source_name"),
        ("alsa_input.usb-FIFINE-00.iec958-stereo", "alsa_input.usb-FIFINE-00.iec958-stereo"),
    ],
)
def test_load_audio_config_accepts_supported_input_device_values(
    monkeypatch, tmp_path, raw_value, expected
):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(f"[audio]\ninput_device = {raw_value!r}\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = audio.load_audio_config()

    assert config.input_device == expected


def test_load_audio_config_warns_and_ignores_int_device():
    warnings_logged: list[str] = []

    class FakeLog:
        def warning(self, event, **kwargs):
            warnings_logged.append(event)

        def info(self, event, **kwargs):
            pass

    config = audio.load_audio_config(log=FakeLog(), data={"audio": {"input_device": 7}})

    assert config.input_device == "auto"
    assert "audio_config_int_device_deprecated" in warnings_logged


@pytest.mark.parametrize(
    "config_body",
    [
        "[audio]\ninput_device = true\n",
        '[audio]\ninput_device = "   "\n',
    ],
)
def test_load_audio_config_rejects_invalid_input_device(monkeypatch, tmp_path, config_body):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(config_body, encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    with pytest.raises(ValueError):
        audio.load_audio_config()


def test_resolve_capture_target_auto_returns_none():
    target = audio.resolve_capture_target("auto")

    assert target is None


def test_resolve_capture_target_default_returns_none():
    target = audio.resolve_capture_target("default")

    assert target is None


def test_resolve_capture_target_auto_is_case_insensitive():
    target = audio.resolve_capture_target("  Auto  ")

    assert target is None


def test_resolve_capture_target_explicit_name_returns_name():
    target = audio.resolve_capture_target("alsa_input.usb-FIFINE-00.iec958-stereo")

    assert target == "alsa_input.usb-FIFINE-00.iec958-stereo"
