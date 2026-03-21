import signal
import subprocess
from typing import cast

import pytest
from spkezy import capture

pytestmark = pytest.mark.unit


def test_check_pw_record_available_raises_when_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="pw-record not found"):
        capture.check_pw_record_available()


def test_check_pw_record_available_passes_when_found(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pw-record")

    capture.check_pw_record_available()


def test_start_capture_spawns_pw_record_with_default_args(monkeypatch):
    spawned_cmds: list[list[str]] = []

    class FakeProc:
        stdout = None
        stderr = None

    def fake_popen(cmd, **kwargs):
        spawned_cmds.append(cmd)
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    capture.start_capture()

    assert len(spawned_cmds) == 1
    cmd = spawned_cmds[0]
    assert cmd[0] == "pw-record"
    assert "--rate=16000" in cmd
    assert "--channels=1" in cmd
    assert "--format=s16" in cmd
    assert "--raw" in cmd
    assert cmd[-1] == "-"
    assert "--target" not in cmd


def test_start_capture_includes_target_when_specified(monkeypatch):
    spawned_cmds: list[list[str]] = []

    class FakeProc:
        stdout = None
        stderr = None

    def fake_popen(cmd, **kwargs):
        spawned_cmds.append(cmd)
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    capture.start_capture(target="alsa_input.usb-FIFINE-00.iec958-stereo")

    cmd = spawned_cmds[0]
    target_idx = cmd.index("--target")
    assert cmd[target_idx + 1] == "alsa_input.usb-FIFINE-00.iec958-stereo"


def test_start_capture_uses_custom_sample_rate(monkeypatch):
    spawned_cmds: list[list[str]] = []

    class FakeProc:
        stdout = None
        stderr = None

    def fake_popen(cmd, **kwargs):
        spawned_cmds.append(cmd)
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    capture.start_capture(sample_rate=48000)

    assert "--rate=48000" in spawned_cmds[0]


def test_stop_capture_sends_sigint_and_reads_remaining(monkeypatch):
    signals_sent: list[int] = []

    class FakeStdout:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

    class FakeStderr:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

    class FakeProc:
        def __init__(self):
            self.stdout = FakeStdout(b"remaining-data")
            self.stderr = FakeStderr(b"")

        def send_signal(self, sig: int) -> None:
            signals_sent.append(sig)

        def wait(self, timeout: float | None = None) -> None:
            pass

    proc = cast(subprocess.Popen[bytes], FakeProc())
    remaining = capture.stop_capture(proc)

    assert remaining == b"remaining-data"
    assert signals_sent == [signal.SIGINT]


def test_stop_capture_falls_back_to_kill_on_timeout(monkeypatch):
    actions: list[str] = []

    class FakeStdout:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

    class FakeStderr:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

    class FakeProc:
        def __init__(self):
            self.stdout = FakeStdout(b"")
            self.stderr = FakeStderr(b"")
            self._killed = False

        def send_signal(self, sig: int) -> None:
            actions.append(f"signal-{sig}")

        def wait(self, timeout: float | None = None) -> None:
            if not self._killed:
                raise subprocess.TimeoutExpired(cmd="pw-record", timeout=3)

        def kill(self) -> None:
            actions.append("killed")
            self._killed = True

    proc = cast(subprocess.Popen[bytes], FakeProc())
    capture.stop_capture(proc)

    assert f"signal-{signal.SIGINT}" in actions
    assert "killed" in actions


def test_get_default_source_name_parses_pactl_output(monkeypatch):
    pactl_output = (
        "Server String: /run/user/1000/pulse/native\n"
        "Default Sink: alsa_output.usb-FIFINE-00.analog-stereo\n"
        "Default Source: alsa_input.usb-FIFINE-00.iec958-stereo\n"
    )

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=pactl_output, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = capture.get_default_source_name()

    assert result == "alsa_input.usb-FIFINE-00.iec958-stereo"


def test_get_default_source_name_returns_none_on_failure(monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("pactl not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = capture.get_default_source_name()

    assert result is None


def test_list_pipewire_sources_parses_pactl_output(monkeypatch):
    pactl_output = (
        "67\talsa_input.usb-FIFINE-00.iec958-stereo\tPipeWire\ts16le 2ch 48000Hz\tRUNNING\n"
        "68\talsa_input.usb-046d_C920-02.analog-stereo\tPipeWire\ts16le 2ch 32000Hz\tSUSPENDED\n"
    )

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=pactl_output, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    sources = capture.list_pipewire_sources()

    assert len(sources) == 2
    assert sources[0]["name"] == "alsa_input.usb-FIFINE-00.iec958-stereo"
    assert sources[0]["state"] == "RUNNING"
    assert sources[1]["name"] == "alsa_input.usb-046d_C920-02.analog-stereo"
    assert sources[1]["format"] == "s16le 2ch 32000Hz"
