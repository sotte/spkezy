import pytest

from spkezy import io

pytestmark = pytest.mark.unit


class LogSpy:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def info(self, event: str, **kwargs):
        self.events.append((event, kwargs))

    def debug(self, event: str, **kwargs):
        self.events.append((event, kwargs))

    def warning(self, event: str, **kwargs):
        self.events.append((event, kwargs))

    def error(self, event: str, **kwargs):
        self.events.append((event, kwargs))


def test_state_manager_starts_idle_and_allows_state_transitions():
    manager = io.StateManager()

    assert manager.state == io.DaemonState.IDLE

    manager.set_state(io.DaemonState.RECORDING)

    assert manager.state == io.DaemonState.RECORDING


def test_state_manager_can_signal_start_and_stop_events():
    manager = io.StateManager()

    manager.signal_start()
    assert manager.wait_for_start(timeout=0.01) is True

    manager.signal_stop()
    assert manager.wait_for_stop(timeout=0.01) is True


def test_state_manager_shutdown_request_is_reported():
    manager = io.StateManager()

    manager.request_shutdown()

    assert manager.is_shutdown_requested() is True


def test_dispatch_command_start_returns_ok_when_idle(tmp_path):
    manager = io.StateManager()
    server = io.UnixSocketServer(tmp_path / "sock", manager, LogSpy())

    response = server._dispatch_command("start")

    assert response["status"] == "ok"
    assert response["state"] == "recording"


def test_dispatch_command_stop_requires_recording_state(tmp_path):
    manager = io.StateManager()
    server = io.UnixSocketServer(tmp_path / "sock", manager, LogSpy())

    response = server._dispatch_command("stop")

    assert response["status"] == "error"

    manager.set_state(io.DaemonState.RECORDING)
    response = server._dispatch_command("stop")

    assert response["status"] == "ok"
    assert response["state"] == "transcribing"


def test_dispatch_command_toggle_handles_idle_recording_and_transcribing(tmp_path):
    manager = io.StateManager()
    server = io.UnixSocketServer(tmp_path / "sock", manager, LogSpy())

    response = server._dispatch_command("toggle")
    assert response["status"] == "ok"
    assert response["action"] == "started"

    manager.set_state(io.DaemonState.RECORDING)
    response = server._dispatch_command("toggle")
    assert response["status"] == "ok"
    assert response["action"] == "stopped"

    manager.set_state(io.DaemonState.TRANSCRIBING)
    response = server._dispatch_command("toggle")
    assert response["status"] == "error"


def test_dispatch_command_status_reflects_current_state(tmp_path):
    manager = io.StateManager()
    manager.set_state(io.DaemonState.TRANSCRIBING)
    server = io.UnixSocketServer(tmp_path / "sock", manager, LogSpy())

    response = server._dispatch_command("status")

    assert response == {"status": "ok", "state": "transcribing"}


def test_dispatch_command_shutdown_sets_shutdown_flag(tmp_path):
    manager = io.StateManager()
    server = io.UnixSocketServer(tmp_path / "sock", manager, LogSpy())

    response = server._dispatch_command("shutdown")

    assert response["status"] == "ok"
    assert manager.is_shutdown_requested() is True


def test_dispatch_command_unknown_returns_error(tmp_path):
    manager = io.StateManager()
    server = io.UnixSocketServer(tmp_path / "sock", manager, LogSpy())

    response = server._dispatch_command("unknown")

    assert response["status"] == "error"
