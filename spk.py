#!/usr/bin/env python3
"""spk Control Client - Send commands to the daemon via Unix socket"""

import json
import os
import socket
import sys
from pathlib import Path


def get_socket_path():
    """Get the daemon socket path (matches daemon.py logic)."""
    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "spk-daemon.sock"
    else:
        return Path("/tmp") / "spk-daemon.sock"


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


def handle_stats_command():
    """Handle the stats command (doesn't require daemon)."""
    # Late import to avoid slow startup for other commands
    from stats import clear_stats, export_stats_json, show_stats

    if "--json" in sys.argv:
        print(export_stats_json())
    elif "--clear" in sys.argv:
        clear_stats()
        print("Stats cleared")
    else:
        # Parse -n argument for number of months
        num_months = 3  # default
        for i, arg in enumerate(sys.argv):
            if arg == "-n" and i + 1 < len(sys.argv):
                try:
                    num_months = int(sys.argv[i + 1])
                except ValueError:
                    pass
        show_stats(num_months=num_months)


def main():
    if len(sys.argv) < 2:
        print("Usage: spk.py <command>")
        print("")
        print("Commands:")
        print("  toggle    - Toggle recording (start if idle, stop if recording)")
        print("  start     - Start recording")
        print("  stop      - Stop recording and transcribe")
        print("  status    - Check daemon status")
        print("  shutdown  - Shutdown the daemon")
        print("  stats     - Show usage statistics and activity heatmap")
        print("    -n N    - Show last N months (default: 3)")
        print("    --json  - Export stats as JSON")
        print("    --clear - Clear all stats")
        print("")
        print("Example:")
        print("  python spk.py toggle")
        print("  python spk.py stats")
        sys.exit(1)

    command = sys.argv[1].lower()

    # Stats command doesn't need daemon
    if command == "stats":
        handle_stats_command()
        return

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
