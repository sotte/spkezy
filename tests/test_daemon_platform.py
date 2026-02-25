import pytest
from spkezy import daemon

pytestmark = pytest.mark.unit


class DummyLog:
    def __init__(self):
        self.entries = []

    def info(self, event, **kwargs):
        self.entries.append((event, kwargs))


class _CudaStub:
    def __init__(self, available=False):
        self._available = available

    def is_available(self):
        return self._available

    def get_device_name(self, index):
        return "NVIDIA"

    def get_device_capability(self):
        return (8, 0)


class _MpsStub:
    def __init__(self, available=False):
        self._available = available

    def is_available(self):
        return self._available


class _BackendsStub:
    def __init__(self, mps_available=False):
        self.mps = _MpsStub(available=mps_available)


class TorchStub:
    def __init__(self, cuda_available=False, mps_available=False):
        self.cuda = _CudaStub(available=cuda_available)
        self.backends = _BackendsStub(mps_available=mps_available)


def test_get_notification_command_uses_notify_send_on_linux(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "linux")

    command = daemon.get_notification_command("Title", "Message")

    assert command == ["notify-send", "-u", "normal", "-t", "2000", "Title", "Message"]


def test_get_notification_command_uses_osascript_on_macos(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "darwin")

    command = daemon.get_notification_command("Title", "Message")

    assert command[0] == "osascript"
    assert command[1] == "-e"
    assert "display notification" in command[2]
    assert '"Message"' in command[2]
    assert '"Title"' in command[2]


def test_get_sound_command_uses_paplay_on_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon.sys, "platform", "linux")

    sound_file = tmp_path / "sound.mp3"
    sound_file.write_text("x", encoding="utf-8")
    command = daemon.get_sound_command(sound_file)

    assert command == ["paplay", str(sound_file)]


def test_get_sound_command_uses_afplay_on_macos(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon.sys, "platform", "darwin")

    sound_file = tmp_path / "sound.mp3"
    sound_file.write_text("x", encoding="utf-8")
    command = daemon.get_sound_command(sound_file)

    assert command == ["afplay", str(sound_file)]


def test_get_autotype_command_uses_wtype_on_linux(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "linux")

    command = daemon.get_autotype_command("hello", delay_ms=10)

    assert command == ["wtype", "-d", "10", "hello"]


def test_get_autotype_command_uses_osascript_on_macos(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "darwin")

    command = daemon.get_autotype_command("hello", delay_ms=10)

    assert command[0] == "osascript"
    assert command[1] == "-e"
    assert "System Events" in command[2]
    assert 'keystroke "hello"' in command[2]


def test_select_inference_device_prefers_cuda():
    log = DummyLog()
    torch_stub = TorchStub(cuda_available=True, mps_available=True)

    device = daemon.select_inference_device(torch_stub, force_cpu=False, log=log)

    assert device == "cuda"


def test_select_inference_device_uses_mps_on_macos_gpu():
    log = DummyLog()
    torch_stub = TorchStub(cuda_available=False, mps_available=True)

    device = daemon.select_inference_device(torch_stub, force_cpu=False, log=log)

    assert device == "mps"
    assert (
        "device_detected",
        {"device": "mps", "note": "Using Apple Silicon GPU (MPS)"},
    ) in log.entries


def test_select_inference_device_falls_back_to_cpu_when_no_accelerator():
    log = DummyLog()
    torch_stub = TorchStub(cuda_available=False, mps_available=False)

    device = daemon.select_inference_device(torch_stub, force_cpu=False, log=log)

    assert device == "cpu"
