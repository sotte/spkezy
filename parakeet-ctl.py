#!/usr/bin/env python3
"""Parakeet Daemon Control Client - Send commands to the daemon via Unix socket"""

import sys
import os
import socket
import json
from pathlib import Path


def get_socket_path():
    """Get the daemon socket path (matches daemon.py logic)."""
    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "parakeet-daemon.sock"
    else:
        return Path("/tmp") / "parakeet-daemon.sock"


def send_command(command: str, socket_path: Path) -> dict:
    """Send a command to the daemon and return the response."""
    if not socket_path.exists():
        print(
            f"❌ Daemon not running (socket not found at {socket_path})",
            file=sys.stderr,
        )
        print("   Start the daemon with: make daemon", file=sys.stderr)
        sys.exit(1)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(socket_path))

        # Send command
        sock.sendall(command.encode() + b"\n")

        # Receive response
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


def main():
    if len(sys.argv) < 2:
        print("Usage: parakeet-ctl.py <command>")
        print("")
        print("Commands:")
        print("  toggle    - Toggle recording (start if idle, stop if recording)")
        print("  start     - Start recording")
        print("  stop      - Stop recording and transcribe")
        print("  status    - Check daemon status")
        print("  shutdown  - Shutdown the daemon")
        print("")
        print("Example:")
        print("  python parakeet-ctl.py toggle")
        print("  python parakeet-ctl.py start")
        print("  python parakeet-ctl.py stop")
        sys.exit(1)

    command = sys.argv[1].lower()
    socket_path = get_socket_path()

    response = send_command(command, socket_path)

    # Pretty print response
    if response.get("status") == "ok":
        if command == "status":
            print(f"✅ Daemon status: {response.get('state', 'unknown')}")
        elif command == "shutdown":
            print(f"✅ {response.get('message', 'Daemon shutting down')}")
        elif command == "toggle":
            action = response.get("action", "unknown")
            state = response.get("state", "unknown")
            print(f"✅ Toggle: {action} recording. State: {state}")
        else:
            state = response.get("state", "unknown")
            print(f"✅ Command '{command}' sent successfully. State: {state}")
    else:
        print(f"❌ Error: {response.get('message', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
