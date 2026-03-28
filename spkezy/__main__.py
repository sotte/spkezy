#!/usr/bin/env python3
"""spkezy Control Client - Send commands to the daemon via Unix socket."""

import sys

from spkezy.io import send_command
from spkezy.runtime import get_socket_path


def handle_stats_command():
    """Handle the stats command (doesn't require daemon)."""
    # Late import to avoid slow startup for other commands
    from spkezy.stats import clear_stats, export_stats_json, show_stats

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
        if sys.stdout.isatty():
            from spkezy.tui import run_tui

            run_tui(num_months=num_months)
        else:
            show_stats(num_months=num_months)


def main():
    if len(sys.argv) < 2:
        print("Usage: spkezy <command>")
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
        print("  spkezy toggle")
        print("  spkezy stats")
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


def daemon_main() -> int:
    from spkezy import daemon

    return daemon.main()


if __name__ == "__main__":
    sys.exit(main())
