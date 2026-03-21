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
    monkeypatch.setattr(daemon, "check_pw_record_available", lambda: None)
    monkeypatch.setattr(daemon, "get_default_source_name", lambda: "alsa_input.usb-FIFINE-00")
    return fake_log


def test_main_exits_when_pw_record_not_found(monkeypatch):
    args = make_args()
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )
    monkeypatch.setattr(
        daemon,
        "check_pw_record_available",
        lambda: (_ for _ in ()).throw(RuntimeError("pw-record not found")),
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


def test_main_uses_auto_capture_target_by_default(monkeypatch):
    args = make_args()
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )

    call_order: list[str] = []

    def fake_load_model(force_cpu, log):
        call_order.append("load_model")
        return object(), "cpu"

    monkeypatch.setattr(daemon, "load_model", fake_load_model)

    result = daemon.main()

    assert result == 0
    assert "load_model" in call_order


def test_main_cli_input_device_overrides_config(monkeypatch):
    args = make_args(input_device="alsa_input.usb-C920-02.analog-stereo")
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )

    resolve_calls: list[str] = []
    original_resolve = daemon.resolve_capture_target

    def tracking_resolve(device_spec, log=None):
        resolve_calls.append(device_spec)
        return original_resolve(device_spec, log=log)

    monkeypatch.setattr(daemon, "resolve_capture_target", tracking_resolve)
    monkeypatch.setattr(daemon, "load_model", lambda force_cpu, log: (object(), "cpu"))

    result = daemon.main()

    assert result == 0
    assert resolve_calls == ["alsa_input.usb-C920-02.analog-stereo"]


def test_main_sends_error_notification_when_pw_record_missing(monkeypatch):
    args = make_args(no_notifications=False)
    setup_main_dependencies(monkeypatch, args)
    monkeypatch.setattr(
        daemon,
        "load_audio_config",
        lambda log=None, data=None: AudioConfig(input_device="auto"),
    )
    monkeypatch.setattr(
        daemon,
        "check_pw_record_available",
        lambda: (_ for _ in ()).throw(RuntimeError("pw-record not found")),
    )

    notifications: list[tuple[str, bool]] = []

    def fake_send_error_notification(error: str, enabled: bool = True, log=None):
        notifications.append((error, enabled))

    monkeypatch.setattr(daemon, "send_error_notification", fake_send_error_notification)

    result = daemon.main()

    assert result == 1
    assert notifications == [("pw-record not found", True)]


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
