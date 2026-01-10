"""Unix socket control helpers for spkezy."""

from __future__ import annotations

import json
import socket
import sys
import threading
from enum import Enum
from pathlib import Path
from typing import Any


class DaemonState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class StateManager:
    """Thread-safe daemon state management."""

    def __init__(self):
        self._state = DaemonState.IDLE
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self._recording_start_event = threading.Event()
        self._recording_stop_event = threading.Event()

    @property
    def state(self) -> DaemonState:
        with self._lock:
            return self._state

    def set_state(self, new_state: DaemonState):
        with self._lock:
            self._state = new_state

    def request_shutdown(self):
        self._shutdown_event.set()

    def is_shutdown_requested(self) -> bool:
        return self._shutdown_event.is_set()

    def wait_for_start(self, timeout: float = 0.1) -> bool:
        """Wait for start command. Returns True if start requested, False if shutdown."""
        while not self.is_shutdown_requested():
            if self._recording_start_event.wait(timeout=timeout):
                self._recording_start_event.clear()
                return True
        return False

    def signal_start(self):
        self._recording_start_event.set()

    def signal_stop(self):
        self._recording_stop_event.set()

    def wait_for_stop(self, timeout: float = 0.1) -> bool:
        """Check if stop was requested. Returns True if stop requested."""
        if self._recording_stop_event.wait(timeout=timeout):
            self._recording_stop_event.clear()
            return True
        return False


def send_command(command: str, socket_path: Path) -> dict:
    """Send a command to the daemon and return the response."""
    if not socket_path.exists():
        print(
            f"❌ Daemon not running (socket not found at {socket_path})",
            file=sys.stderr,
        )
        print("   Start the daemon with: spkezy-daemon (or make daemon)", file=sys.stderr)
        sys.exit(1)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(socket_path))

        sock.sendall(command.encode() + b"\n")

        response_data = sock.recv(4096).decode().strip()
        sock.close()

        try:
            return json.loads(response_data)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid response from daemon"}

    except ConnectionRefusedError:
        print(f"❌ Could not connect to daemon at {socket_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


class UnixSocketServer:
    """Unix socket server for daemon control."""

    def __init__(self, socket_path: Path, state_manager: StateManager, log: Any):
        self.socket_path = socket_path
        self.state_manager = state_manager
        self.log = log
        self.sock: socket.socket | None = None

    def start(self) -> bool:
        """Set up and start the socket server."""
        if self.socket_path.exists():
            try:
                test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                test_sock.connect(str(self.socket_path))
                test_sock.close()
                self.log.error("daemon_already_running", socket_path=str(self.socket_path))
                return False
            except ConnectionRefusedError:
                self.socket_path.unlink()
                self.log.info("removed_stale_socket", socket_path=str(self.socket_path))

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(str(self.socket_path))
        self.sock.listen(5)

        self.log.info("socket_server_started", socket_path=str(self.socket_path))

        server_thread = threading.Thread(target=self._server_loop, daemon=True)
        server_thread.start()

        return True

    def _server_loop(self):
        """Accept connections and handle commands in separate threads."""
        assert self.sock is not None
        while not self.state_manager.is_shutdown_requested():
            try:
                self.sock.settimeout(0.5)
                client_sock, _ = self.sock.accept()
                threading.Thread(
                    target=self._handle_command, args=(client_sock,), daemon=True
                ).start()
            except TimeoutError:
                continue
            except Exception as e:
                if not self.state_manager.is_shutdown_requested():
                    self.log.error("socket_server_error", error=str(e))
                break

        self.log.info("socket_server_stopped")

    def _handle_command(self, client_socket):
        """Handle incoming command from client."""
        try:
            data = client_socket.recv(1024).decode().strip()
            if not data:
                return

            try:
                command = json.loads(data)
                cmd = command.get("action", "").lower()
            except json.JSONDecodeError:
                cmd = data.lower()

            self.log.debug("command_received", command=cmd)

            response = self._dispatch_command(cmd)
            client_socket.sendall((json.dumps(response) + "\n").encode())

        except Exception as e:
            self.log.error("command_handling_error", error=str(e))
            try:
                error_response = {"status": "error", "message": str(e)}
                client_socket.sendall((json.dumps(error_response) + "\n").encode())
            except Exception:
                pass
        finally:
            client_socket.close()

    def _dispatch_command(self, cmd: str) -> dict:
        """Dispatch command to appropriate handler."""
        current_state = self.state_manager.state

        if cmd == "start":
            if current_state == DaemonState.IDLE:
                self.state_manager.signal_start()
                self.log.info("command_start")
                return {"status": "ok", "state": "recording"}
            return {
                "status": "error",
                "message": f"Cannot start, currently {current_state.value}",
            }

        if cmd == "stop":
            if current_state == DaemonState.RECORDING:
                self.state_manager.signal_stop()
                self.log.info("command_stop")
                return {"status": "ok", "state": "transcribing"}
            return {
                "status": "error",
                "message": f"Cannot stop, currently {current_state.value}",
            }

        if cmd == "toggle":
            if current_state == DaemonState.IDLE:
                self.state_manager.signal_start()
                self.log.info("command_toggle", action="started")
                return {"status": "ok", "action": "started", "state": "recording"}
            if current_state == DaemonState.RECORDING:
                self.state_manager.signal_stop()
                self.log.info("command_toggle", action="stopped")
                return {"status": "ok", "action": "stopped", "state": "transcribing"}
            return {
                "status": "error",
                "message": f"Cannot toggle while {current_state.value}",
            }

        if cmd == "status":
            return {"status": "ok", "state": current_state.value}

        if cmd == "shutdown":
            self.log.info("command_shutdown")
            self.state_manager.request_shutdown()
            return {"status": "ok", "message": "shutting down"}

        return {"status": "error", "message": f"Unknown command: {cmd}"}

    def cleanup(self):
        """Clean up socket resources."""
        if self.sock:
            self.sock.close()
        if self.socket_path.exists():
            self.socket_path.unlink()
        self.log.info("socket_cleanup_complete")
