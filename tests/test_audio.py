import pytest
from spkezy import audio

pytestmark = pytest.mark.unit


class FakePyAudio:
    def __init__(self, devices, supported_rates, default_input_index=0, openable_rates=None):
        self._devices = devices
        self._supported_rates = supported_rates
        self._default_input_index = default_input_index
        self._openable_rates = openable_rates if openable_rates is not None else supported_rates
        self.open_calls: list[tuple[int, int]] = []

    def get_device_count(self):
        return len(self._devices)

    def get_device_info_by_index(self, index):
        return self._devices[index]

    def get_default_input_device_info(self):
        return self._devices[self._default_input_index]

    def is_format_supported(self, rate, input_device, input_channels, input_format):
        return rate in self._supported_rates.get(input_device, set())

    def open(
        self,
        *,
        format,
        channels,
        rate,
        input,
        input_device_index,
        frames_per_buffer,
    ):
        self.open_calls.append((input_device_index, rate))
        if rate not in self._openable_rates.get(input_device_index, set()):
            raise OSError("boom")
        return FakeStream()


class FakeStream:
    def close(self):
        return None


def test_load_audio_config_defaults_to_auto(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = audio.load_audio_config()

    assert config.input_device == "auto"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("auto", "auto"),
        ("sysdefault", "sysdefault"),
        (" FIFINE K670 Microphone ", "FIFINE K670 Microphone"),
        (7, 7),
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


def test_resolve_input_device_index_prefers_exact_name_match():
    pa = FakePyAudio(
        devices=[
            {
                "index": 0,
                "name": "FIFINE K670 Microphone: USB Audio (hw:0,0)",
                "maxInputChannels": 2,
            },
            {"index": 1, "name": "sysdefault", "maxInputChannels": 128},
        ],
        supported_rates={0: {44100}, 1: {16000, 48000}},
        default_input_index=0,
    )

    device_index = audio.resolve_input_device_index(pa, "sysdefault")

    assert device_index == 1


def test_resolve_input_device_index_auto_prefers_sysdefault_when_available():
    pa = FakePyAudio(
        devices=[
            {"index": 0, "name": "FIFINE K670 Microphone", "maxInputChannels": 2},
            {"index": 1, "name": "sysdefault", "maxInputChannels": 128},
        ],
        supported_rates={0: {44100}, 1: {16000, 48000}},
        default_input_index=0,
    )

    device_index = audio.resolve_input_device_index(pa, "auto")

    assert device_index == 1


def test_resolve_input_device_index_auto_falls_back_to_default_input_when_sysdefault_missing():
    pa = FakePyAudio(
        devices=[
            {"index": 0, "name": "FIFINE K670 Microphone", "maxInputChannels": 2},
            {"index": 1, "name": "USB Webcam", "maxInputChannels": 2},
        ],
        supported_rates={0: {44100}, 1: {16000, 32000}},
        default_input_index=1,
    )

    device_index = audio.resolve_input_device_index(pa, "auto")

    assert device_index == 1


def test_resolve_input_device_index_rejects_partial_name_matches():
    pa = FakePyAudio(
        devices=[
            {"index": 0, "name": "FIFINE K670 Microphone", "maxInputChannels": 2},
            {"index": 1, "name": "sysdefault", "maxInputChannels": 128},
        ],
        supported_rates={0: {44100}, 1: {16000, 48000}},
        default_input_index=0,
    )

    with pytest.raises(ValueError, match="Use an exact device name or index"):
        audio.resolve_input_device_index(pa, "FIFINE")


def test_resolve_input_device_index_accepts_numeric_string():
    pa = FakePyAudio(
        devices=[{"index": 0, "name": "sysdefault", "maxInputChannels": 128}],
        supported_rates={0: {16000, 48000}},
        default_input_index=0,
    )

    device_index = audio.resolve_input_device_index(pa, "0")

    assert device_index == 0


def test_choose_input_sample_rate_falls_back_to_device_default_when_16000_unsupported():
    pa = FakePyAudio(
        devices=[
            {
                "index": 0,
                "name": "FIFINE K670 Microphone: USB Audio (hw:0,0)",
                "maxInputChannels": 2,
                "defaultSampleRate": 44100.0,
            }
        ],
        supported_rates={0: {44100, 48000}},
    )

    sample_rate = audio.choose_input_sample_rate(pa, 0, input_format=8)

    assert sample_rate == 44100


def test_validate_audio_input_stream_raises_when_stream_open_fails():
    pa = FakePyAudio(
        devices=[
            {
                "index": 0,
                "name": "sysdefault",
                "maxInputChannels": 128,
                "defaultSampleRate": 48000.0,
            }
        ],
        supported_rates={0: {16000}},
        openable_rates={0: set()},
    )

    with pytest.raises(ValueError, match="Unable to open audio input 'sysdefault' at 16000Hz"):
        audio.validate_audio_input_stream(pa, 0, 16000, input_format=8)


def test_validate_audio_input_stream_opens_selected_device_and_rate():
    pa = FakePyAudio(
        devices=[
            {
                "index": 0,
                "name": "sysdefault",
                "maxInputChannels": 128,
                "defaultSampleRate": 48000.0,
            }
        ],
        supported_rates={0: {16000}},
    )

    audio.validate_audio_input_stream(pa, 0, 16000, input_format=8)

    assert pa.open_calls == [(0, 16000)]
