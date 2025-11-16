#!/usr/bin/env python3
"""Parakeet TDT 0.6B v3 - Daemon Mode (v2 with structlog)"""

import sys
import argparse
from pathlib import Path
import logging
import structlog

# ===== CLI Arguments =====

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parakeet TDT 0.6B v3 daemon - keeps model loaded, listens on Unix socket for commands.",
        epilog="""Examples:
  python daemon_v2.py
  python daemon_v2.py --debug
  python daemon_v2.py --cpu
  python daemon_v2.py --socket-path /tmp/parakeet.sock
""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Verbose diagnostics: device, timings, GPU memory",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU inference",
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Do not copy transcript to clipboard",
    )
    parser.add_argument(
        "--no-auto-type",
        action="store_true",
        help="Disable auto-typing transcript (falls back to clipboard)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Debug log file path (only used with --debug)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List audio input devices and exit",
    )
    parser.add_argument(
        "--input-device",
        type=int,
        default=None,
        help="PyAudio input device index",
    )
    parser.add_argument(
        "--socket-path",
        default=None,
        help="Unix socket path (default: $XDG_RUNTIME_DIR/parakeet-daemon.sock or /tmp/parakeet-daemon.sock)",
    )
    parser.add_argument(
        "--no-notifications",
        action="store_true",
        help="Disable desktop notifications",
    )
    return parser.parse_args()


# ===== Logging Configuration =====

def configure_logging(debug: bool, log_file: str | None):
    """Configure structlog for console and optional file output."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        # Use human-readable console output for stderr, JSON for file logging
        structlog.dev.ConsoleRenderer() if not log_file else structlog.processors.JSONRenderer(),
    ]

    # Set minimum log level
    min_level = logging.DEBUG if debug else logging.INFO

    # Determine output file
    output_file = sys.stderr
    if log_file:
        output_file = open(log_file, "w")  # noqa: SIM115
        # Note: File handle kept open for daemon lifetime, closed on process exit

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(min_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output_file),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


# ===== Main =====

def main():
    args = parse_arguments()
    log = configure_logging(args.debug, args.log_file)

    log.info("daemon_starting", version="2.0")

    # TODO: Implement rest of daemon

    return 0


if __name__ == "__main__":
    sys.exit(main())
