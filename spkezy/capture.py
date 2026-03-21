"""Audio capture via PipeWire (pw-record subprocess).

Replaces PyAudio/PortAudio with a PipeWire-native approach that always follows
the system default audio source. When the user switches their default mic in
system settings, pw-record automatically captures from the new device.
"""

from __future__ import annotations

import shutil
import signal
import subprocess
from typing import Any

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_FORMAT = "s16"  # 16-bit signed PCM
CHUNK_SIZE = 2048


def check_pw_record_available() -> None:
    """Verify pw-record is installed. Raises RuntimeError if not found."""
    if shutil.which("pw-record") is None:
        raise RuntimeError(
            "pw-record not found. "
            "PipeWire must be installed and running. "
            "Check: systemctl --user status pipewire"
        )


def start_capture(
    sample_rate: int = SAMPLE_RATE,
    target: str | None = None,
    log: Any | None = None,
) -> subprocess.Popen[bytes]:
    """Start a pw-record subprocess that streams raw PCM to stdout.

    Args:
        sample_rate: Capture sample rate in Hz (default 16000).
        target: PipeWire source target name, or None for system default.
        log: Optional structlog logger.

    Returns:
        The running pw-record subprocess. Read PCM from proc.stdout.
    """
    cmd = [
        "pw-record",
        f"--rate={sample_rate}",
        f"--channels={CHANNELS}",
        f"--format={SAMPLE_FORMAT}",
        "--raw",
    ]
    if target:
        cmd.extend(["--target", target])
    cmd.append("-")  # write to stdout

    if log:
        log.debug("capture_starting", cmd=" ".join(cmd), target=target or "system-default")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def stop_capture(proc: subprocess.Popen[bytes], log: Any | None = None) -> bytes:
    """Stop a pw-record subprocess and return any remaining buffered PCM data.

    Sends SIGINT for clean shutdown, falls back to SIGKILL on timeout.
    """
    remaining = b""
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=3)
    except ProcessLookupError:
        pass  # already exited
    except subprocess.TimeoutExpired:
        if log:
            log.warning("capture_sigint_timeout", msg="falling back to SIGKILL")
        proc.kill()
        proc.wait()

    if proc.stdout:
        remaining = proc.stdout.read() or b""

    stderr_output = ""
    if proc.stderr:
        stderr_output = proc.stderr.read().decode(errors="replace").strip()

    if stderr_output and log:
        log.debug("capture_stderr", stderr=stderr_output)

    return remaining


def get_default_source_name() -> str | None:
    """Query PipeWire/PulseAudio for the current default source name."""
    try:
        result = subprocess.run(
            ["pactl", "info"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.strip().startswith("Default Source:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def list_pipewire_sources() -> list[dict[str, str]]:
    """List available PipeWire audio sources via pactl.

    Returns a list of dicts with keys: id, name, driver, format, state.
    """
    try:
        result = subprocess.run(
            ["pactl", "list", "short", "sources"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return []

    sources: list[dict[str, str]] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 5:
            sources.append(
                {
                    "id": parts[0],
                    "name": parts[1],
                    "driver": parts[2],
                    "format": parts[3],
                    "state": parts[4],
                }
            )
    return sources
