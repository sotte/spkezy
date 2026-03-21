from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from spkezy import daemon
from spkezy.audio import AudioConfig
from spkezy.output import OutputConfig
from spkezy.postprocess import PostprocessConfig

pytestmark = pytest.mark.unit


class FakeLog:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def info(self, event: str, **kwargs):
        self.events.append((event, kwargs))

    def warning(self, event: str, **kwargs):
        self.events.append((event, kwargs))

    def error(self, event: str, **kwargs):
        self.events.append((event, kwargs))

    def debug(self, event: str, **kwargs):
        self.events.append((event, kwargs))


class FakeStateManager:
    def request_shutdown(self):
        return None

    def wait_for_start(self):
        return False

    def is_shutdown_requested(self):
        return False


class FakeSocketServer:
    def __init__(self, socket_path, state_manager, log):
        self.socket_path = socket_path
        self.state_manager = state_manager
        self.log = log
        self.cleaned_up = False

    def start(self):
        return True

    def cleanup(self):
        self.cleaned_up = True


def make_args(*, input_device=None, no_notifications=True):
    return argparse.Namespace(
        debug=False,
        cpu=False,
        log_file=None,
        list_devices=False,
        input_device=input_device,
        socket_path=None,
        no_notifications=no_notifications,
    )


def setup_main_dependencies(monkeypatch, args):
    fake_log = FakeLog()
    monkeypatch.setattr(daemon, "parse_arguments", lambda: args)
    monkeypatch.setattr(daemon, "configure_logging", lambda debug, log_file: fake_log)
    monkeypatch.setattr(daemon, "get_socket_path", lambda override=None: Path("/tmp/test.sock"))
    monkeypatch.setattr(daemon, "StateManager", FakeStateManager)
    monkeypatch.setattr(daemon, "UnixSocketServer", FakeSocketServer)
    monkeypatch.setattr(daemon, "setup_signal_handlers", lambda state_manager: None)
    monkeypatch.setattr(daemon, "send_notification", lambda *args, **kwargs: None)
    monkeypatch.setattr(daemon, "play_sound", lambda *args, **kwargs: None)
    monkeypatch.setattr(daemon, "load_toml_config", lambda log=None: {})
    monkeypatch.setattr(
        daemon,
        "load_postprocess_config",
        lambda log=None, data=None: PostprocessConfig(),
    )
    monkeypatch.setattr(
        daemon,
        "load_output_config",
        lambda log=None, data=None: OutputConfig(),
    )
    return fake_log


def test_main_fails_before_model_load_when_audio_input_invalid(monkeypatch):
    args = make_args()
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )
    monkeypatch.setattr(
        daemon,
        "resolve_audio_input",
        lambda device_spec, log=None: (_ for _ in ()).throw(ValueError("bad device")),
    )

    model_load_called = False

    def fake_load_model(force_cpu, log):
        nonlocal model_load_called
        model_load_called = True
        return object(), "cpu"

    monkeypatch.setattr(daemon, "load_model", fake_load_model)

    result = daemon.main()

    assert result == 1
    assert model_load_called is False


def test_main_uses_configured_input_device_and_validates_audio_before_model_load(monkeypatch):
    args = make_args()
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )

    call_order: list[tuple[str, str | None]] = []

    def fake_resolve_audio_input(device_spec, log=None):
        call_order.append(("resolve_audio_input", device_spec))
        return 7, 16000, "sysdefault"

    def fake_load_model(force_cpu, log):
        call_order.append(("load_model", None))
        return object(), "cpu"

    monkeypatch.setattr(daemon, "resolve_audio_input", fake_resolve_audio_input)
    monkeypatch.setattr(daemon, "load_model", fake_load_model)

    result = daemon.main()

    assert result == 0
    assert call_order == [("resolve_audio_input", "auto"), ("load_model", None)]


def test_main_cli_input_device_overrides_config(monkeypatch):
    args = make_args(input_device="sysdefault")
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )

    selected_devices: list[str] = []

    def fake_resolve_audio_input(device_spec, log=None):
        selected_devices.append(device_spec)
        return 7, 16000, "sysdefault"

    monkeypatch.setattr(daemon, "resolve_audio_input", fake_resolve_audio_input)
    monkeypatch.setattr(daemon, "load_model", lambda force_cpu, log: (object(), "cpu"))

    result = daemon.main()

    assert result == 0
    assert selected_devices == ["sysdefault"]


def test_main_sends_error_notification_when_audio_input_is_invalid(monkeypatch):
    args = make_args(no_notifications=False)
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )
    monkeypatch.setattr(
        daemon,
        "resolve_audio_input",
        lambda device_spec, log=None: (_ for _ in ()).throw(ValueError("Device busy")),
    )

    notifications: list[tuple[str, bool]] = []

    def fake_send_error_notification(error: str, enabled: bool = True, log=None):
        notifications.append((error, enabled))

    monkeypatch.setattr(daemon, "send_error_notification", fake_send_error_notification)

    result = daemon.main()

    assert result == 1
    assert notifications == [("Device busy", True)]


def test_send_error_notification_truncates_message(monkeypatch):
    sent: list[tuple[str, str, bool]] = []

    def fake_send_notification(title: str, message: str, enabled: bool = True, log=None):
        sent.append((title, message, enabled))

    monkeypatch.setattr(daemon, "send_notification", fake_send_notification)

    daemon.send_error_notification("x" * 400, enabled=True)

    assert sent[0][0] == "🥃 spkezy - Error"
    assert sent[0][2] is True
    assert sent[0][1].endswith("...")
    assert len(sent[0][1]) == 220
