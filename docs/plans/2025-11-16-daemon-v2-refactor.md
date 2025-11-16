# Daemon v2 Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite daemon.py with structlog, clean architecture, and lazy imports while maintaining all existing functionality.

**Architecture:** Single-file daemon with functional design (classes only for state/socket management). Lazy imports for heavy libraries (NeMo/PyTorch) to keep `--help` and `--list-devices` fast. Structlog for all logging (INFO for user-facing events, DEBUG for internals). No custom output silencing - let structlog handle everything.

**Tech Stack:** Python 3.11+, structlog, NeMo ASR, PyTorch, PyAudio, pyperclip, wtype (Wayland auto-typing)

---

## Task 1: Set up structlog configuration and basic CLI

**Files:**
- Create: `daemon_v2.py`

**Step 1: Create basic structure with argparse and structlog**

Create `daemon_v2.py`:

```python
#!/usr/bin/env python3
"""Parakeet TDT 0.6B v3 - Daemon Mode (v2 with structlog)"""

import sys
import argparse
from pathlib import Path
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
        structlog.dev.ConsoleRenderer() if not log_file else structlog.processors.JSONRenderer(),
    ]

    if debug:
        level = "DEBUG"
    else:
        level = "INFO"

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib.BoundLogger, level.upper(), structlog.stdlib.logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr if not log_file else open(log_file, "w")),
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
```

**Step 2: Test basic CLI**

Run: `python daemon_v2.py --help`
Expected: Help message displays all arguments

Run: `python daemon_v2.py`
Expected: Logs "daemon_starting" with INFO level

Run: `python daemon_v2.py --debug`
Expected: Logs "daemon_starting" with DEBUG level visible

**Step 3: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add basic CLI and structlog setup"
```

---

## Task 2: Add socket path detection and --list-devices

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add socket path logic**

Add after `parse_arguments()`:

```python
import os

def get_socket_path(args_socket_path: str | None) -> Path:
    """Determine Unix socket path from args or environment."""
    if args_socket_path:
        return Path(args_socket_path)

    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "parakeet-daemon.sock"

    return Path("/tmp") / "parakeet-daemon.sock"
```

**Step 2: Add list-devices fast path (lazy import)**

Add before `main()`:

```python
def list_audio_devices():
    """List available audio input devices and exit."""
    import pyaudio  # Lazy import - only needed for this command

    pa = pyaudio.PyAudio()
    try:
        count = pa.get_device_count()
        print("Input devices:")
        for i in range(count):
            info = pa.get_device_info_by_index(i)
            if int(info.get("maxInputChannels", 0)) > 0:
                name = info.get("name", "unknown")
                rate = int(info.get("defaultSampleRate", 0))
                print(f"- id={i} name='{name}' rate={rate}Hz")
    finally:
        pa.terminate()
```

**Step 3: Update main() to use these**

Update `main()`:

```python
def main():
    args = parse_arguments()

    # Fast path: list devices
    if args.list_devices:
        try:
            list_audio_devices()
            return 0
        except Exception as e:
            print(f"Error listing devices: {e}")
            return 1

    log = configure_logging(args.debug, args.log_file)
    socket_path = get_socket_path(args.socket_path)

    log.info("daemon_starting", version="2.0", socket_path=str(socket_path))

    # TODO: Implement rest of daemon

    return 0
```

**Step 4: Test**

Run: `python daemon_v2.py --list-devices`
Expected: Lists audio devices, exits quickly (no heavy imports)

Run: `python daemon_v2.py --socket-path /tmp/test.sock`
Expected: Logs with socket_path="/tmp/test.sock"

**Step 5: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add socket path detection and list-devices"
```

---

## Task 3: Add state management and signal handling

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add state enum and management**

Add near the top (after imports):

```python
import threading
import signal
import atexit
from enum import Enum

# ===== Daemon State =====

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
```

**Step 2: Add signal handlers**

Add before `main()`:

```python
def setup_signal_handlers(state_manager: StateManager):
    """Set up graceful shutdown on SIGINT/SIGTERM."""

    def signal_handler(signum, frame):
        state_manager.request_shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Suppress KeyboardInterrupt traceback
    def no_kbi_traceback(exc_type, exc, tb):
        if exc_type is KeyboardInterrupt:
            return
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = no_kbi_traceback
```

**Step 3: Update main() to use StateManager**

Update `main()`:

```python
def main():
    args = parse_arguments()

    # Fast path: list devices
    if args.list_devices:
        try:
            list_audio_devices()
            return 0
        except Exception as e:
            print(f"Error listing devices: {e}")
            return 1

    log = configure_logging(args.debug, args.log_file)
    socket_path = get_socket_path(args.socket_path)
    state_manager = StateManager()

    setup_signal_handlers(state_manager)

    log.info("daemon_starting", version="2.0", socket_path=str(socket_path))

    # TODO: Implement rest of daemon

    return 0
```

**Step 4: Test signal handling**

Run: `python daemon_v2.py` then press Ctrl+C
Expected: Exits gracefully without traceback

**Step 5: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add state management and signal handling"
```

---

## Task 4: Add notification and sound helpers

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add notification and sound functions**

Add before `main()`:

```python
import subprocess

# ===== Notifications & Audio Feedback =====

def send_notification(title: str, message: str, enabled: bool = True, log=None):
    """Send desktop notification via notify-send."""
    if not enabled:
        return

    try:
        subprocess.run(
            ["notify-send", "-u", "normal", "-t", "2000", title, message],
            check=False,
            capture_output=True,
        )
        if log:
            log.debug("notification_sent", title=title, message=message)
    except Exception as e:
        if log:
            log.warning("notification_failed", error=str(e))


def play_sound(log=None):
    """Play sound.mp3 via paplay (non-blocking)."""
    try:
        sound_file = Path(__file__).parent / "sound.mp3"
        if not sound_file.exists():
            return

        subprocess.Popen(
            ["paplay", str(sound_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        if log:
            log.debug("sound_playback_failed", error=str(e))


def auto_type_text(text: str, log=None):
    """Auto-type text using wtype (Wayland)."""
    try:
        subprocess.run(
            ["wtype", text],
            check=True,
            capture_output=True,
        )
        if log:
            log.info("auto_typed", length=len(text))
    except FileNotFoundError:
        if log:
            log.warning("wtype_not_found", message="install wtype package")
        raise
    except subprocess.CalledProcessError as e:
        if log:
            log.warning("wtype_failed", exit_code=e.returncode, stderr=e.stderr.decode())
        raise
```

**Step 2: Test (manual)**

These functions will be tested in integration. No separate test needed at this stage.

**Step 3: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add notification and sound helpers"
```

---

## Task 5: Add model loading with lazy imports

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add model loading function**

Add before `main()`:

```python
import time
import warnings

# ===== Model Loading =====

def load_model(force_cpu: bool, log):
    """Load NeMo ASR model with lazy imports."""
    log.info("model_loading_start", model="nvidia/parakeet-tdt-0.6b-v3")

    # Lazy imports - only load when actually starting daemon
    import torch
    import nemo.collections.asr as nemo_asr

    # Suppress warnings
    warnings.filterwarnings("ignore")

    # Detect device
    use_cuda = torch.cuda.is_available() and not force_cpu
    device = "cuda" if use_cuda else "cpu"

    # Log device info
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        if use_cuda:
            cap = torch.cuda.get_device_capability()
            log.info("device_detected", device="cuda", gpu=gpu_name, cuda_capability=f"{cap[0]}.{cap[1]}")
        else:
            log.info("device_detected", device="cpu", note="GPU available but using CPU (--cpu flag)", gpu=gpu_name)
    else:
        log.info("device_detected", device="cpu", note="No CUDA GPU detected")

    # Load model
    t_start = time.perf_counter()
    model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3")
    t_end = time.perf_counter()

    # Move to device
    model.to(device)
    model.eval()

    log.info("model_loaded", device=device, load_time_seconds=round(t_end - t_start, 1))

    return model, device
```

**Step 2: Update main() to load model**

Update `main()` to add model loading (replace TODO):

```python
def main():
    args = parse_arguments()

    # Fast path: list devices
    if args.list_devices:
        try:
            list_audio_devices()
            return 0
        except Exception as e:
            print(f"Error listing devices: {e}")
            return 1

    log = configure_logging(args.debug, args.log_file)
    socket_path = get_socket_path(args.socket_path)
    state_manager = StateManager()

    setup_signal_handlers(state_manager)

    log.info("daemon_starting", version="2.0", socket_path=str(socket_path))

    # Load model
    try:
        model, device = load_model(args.cpu, log)
    except Exception as e:
        log.error("model_load_failed", error=str(e))
        return 1

    send_notification("Parakeet Ready", f"Model loaded on {device}", not args.no_notifications, log)

    log.info("daemon_ready")

    # TODO: Socket server and main loop

    return 0
```

**Step 3: Test model loading**

Run: `python daemon_v2.py --cpu --debug`
Expected: Logs show model loading progress, device detection, load time

**Step 4: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add model loading with lazy imports"
```

---

## Task 6: Add socket server and command handling

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add socket server class**

Add before `main()`:

```python
import socket
import json

# ===== Socket Server =====

class UnixSocketServer:
    """Unix socket server for daemon control."""

    def __init__(self, socket_path: Path, state_manager: StateManager, log):
        self.socket_path = socket_path
        self.state_manager = state_manager
        self.log = log
        self.sock = None

    def start(self):
        """Set up and start the socket server."""
        # Clean up stale socket
        if self.socket_path.exists():
            try:
                # Try to connect - if it works, daemon is already running
                test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                test_sock.connect(str(self.socket_path))
                test_sock.close()
                self.log.error("daemon_already_running", socket_path=str(self.socket_path))
                return False
            except ConnectionRefusedError:
                # Stale socket, remove it
                self.socket_path.unlink()
                self.log.info("removed_stale_socket", socket_path=str(self.socket_path))

        # Create socket
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(str(self.socket_path))
        self.sock.listen(5)

        self.log.info("socket_server_started", socket_path=str(self.socket_path))

        # Start server thread
        server_thread = threading.Thread(target=self._server_loop, daemon=True)
        server_thread.start()

        return True

    def _server_loop(self):
        """Accept connections and handle commands in separate threads."""
        while not self.state_manager.is_shutdown_requested():
            try:
                self.sock.settimeout(0.5)
                client_sock, _ = self.sock.accept()
                # Handle each command in a separate thread
                threading.Thread(
                    target=self._handle_command,
                    args=(client_sock,),
                    daemon=True
                ).start()
            except socket.timeout:
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
                # Simple string command
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
            else:
                return {"status": "error", "message": f"Cannot start, currently {current_state.value}"}

        elif cmd == "stop":
            if current_state == DaemonState.RECORDING:
                self.state_manager.signal_stop()
                self.log.info("command_stop")
                return {"status": "ok", "state": "transcribing"}
            else:
                return {"status": "error", "message": f"Cannot stop, currently {current_state.value}"}

        elif cmd == "toggle":
            if current_state == DaemonState.IDLE:
                self.state_manager.signal_start()
                self.log.info("command_toggle", action="started")
                return {"status": "ok", "action": "started", "state": "recording"}
            elif current_state == DaemonState.RECORDING:
                self.state_manager.signal_stop()
                self.log.info("command_toggle", action="stopped")
                return {"status": "ok", "action": "stopped", "state": "transcribing"}
            else:
                return {"status": "error", "message": f"Cannot toggle while {current_state.value}"}

        elif cmd == "status":
            return {"status": "ok", "state": current_state.value}

        elif cmd == "shutdown":
            self.log.info("command_shutdown")
            self.state_manager.request_shutdown()
            return {"status": "ok", "message": "shutting down"}

        else:
            return {"status": "error", "message": f"Unknown command: {cmd}"}

    def cleanup(self):
        """Clean up socket resources."""
        if self.sock:
            self.sock.close()
        if self.socket_path.exists():
            self.socket_path.unlink()
        self.log.info("socket_cleanup_complete")
```

**Step 2: Update main() to start socket server**

Update `main()`:

```python
def main():
    args = parse_arguments()

    # Fast path: list devices
    if args.list_devices:
        try:
            list_audio_devices()
            return 0
        except Exception as e:
            print(f"Error listing devices: {e}")
            return 1

    log = configure_logging(args.debug, args.log_file)
    socket_path = get_socket_path(args.socket_path)
    state_manager = StateManager()

    setup_signal_handlers(state_manager)

    log.info("daemon_starting", version="2.0", socket_path=str(socket_path))

    # Load model
    try:
        model, device = load_model(args.cpu, log)
    except Exception as e:
        log.error("model_load_failed", error=str(e))
        return 1

    # Start socket server
    socket_server = UnixSocketServer(socket_path, state_manager, log)
    if not socket_server.start():
        return 1

    send_notification("Parakeet Ready", f"Model loaded on {device}", not args.no_notifications, log)

    log.info("daemon_ready", commands=["start", "stop", "toggle", "status", "shutdown"])

    # TODO: Main recording loop

    # Wait for shutdown
    while not state_manager.is_shutdown_requested():
        time.sleep(0.1)

    # Cleanup
    socket_server.cleanup()
    log.info("daemon_stopped")

    return 0
```

**Step 3: Test socket server**

Terminal 1: `python daemon_v2.py --cpu`
Terminal 2: `python parakeet-ctl.py status`
Expected: Returns `{"status": "ok", "state": "idle"}`

Terminal 2: `python parakeet-ctl.py shutdown`
Expected: Daemon logs shutdown and exits

**Step 4: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add socket server and command handling"
```

---

## Task 7: Add audio recording

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add audio recording function**

Add before `main()`:

```python
import wave
import tempfile

# ===== Audio Recording =====

def record_audio(
    state_manager: StateManager,
    sample_rate: int = 16000,
    device_index: int | None = None,
    log=None,
) -> bytes | None:
    """Record audio until stop event or shutdown."""
    import pyaudio  # Lazy import

    p = pyaudio.PyAudio()

    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024,
        )
    except Exception as e:
        if log:
            log.error("audio_stream_open_failed", error=str(e))
        p.terminate()
        return None

    frames = []

    if log:
        log.info("recording_started")

    state_manager.set_state(DaemonState.RECORDING)

    try:
        while not state_manager.is_shutdown_requested():
            # Check for stop signal
            if state_manager.wait_for_stop(timeout=0):
                if log:
                    log.info("recording_stopped", frames=len(frames))
                break

            try:
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            except Exception:
                continue
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    return b"".join(frames) if frames else None


def save_audio_to_wav(audio_data: bytes, sample_rate: int = 16000) -> str:
    """Save audio data to temporary WAV file. Returns path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)

    return tmp.name
```

**Step 2: Test (integrated in next task)**

This will be tested as part of the main loop.

**Step 3: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add audio recording"
```

---

## Task 8: Add transcription and output handling

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add transcription function**

Add before `main()`:

```python
# ===== Transcription =====

def transcribe_audio(model, audio_path: str, device: str, log) -> str:
    """Transcribe audio file using NeMo model."""
    log.info("transcription_started")

    t_start = time.perf_counter()
    try:
        result = model.transcribe([audio_path], verbose=False)

        if isinstance(result, list) and len(result) > 0:
            first = result[0]
            transcript = getattr(first, "text", first if isinstance(first, str) else str(first))
        else:
            transcript = str(result)

        t_end = time.perf_counter()
        log.info("transcription_completed", length=len(transcript), time_seconds=round(t_end - t_start, 3))

        return transcript

    except Exception as e:
        log.error("transcription_failed", error=str(e))
        raise


def handle_transcript_output(
    transcript: str,
    auto_type: bool,
    use_clipboard: bool,
    log,
):
    """Handle transcript output: auto-type or clipboard."""
    if auto_type:
        try:
            auto_type_text(transcript, log)
        except Exception as e:
            log.warning("auto_type_failed", error=str(e))
            # Fall back to clipboard if auto-type fails
            if use_clipboard:
                copy_to_clipboard(transcript, log)
    elif use_clipboard:
        copy_to_clipboard(transcript, log)


def copy_to_clipboard(text: str, log):
    """Copy text to clipboard using pyperclip."""
    import pyperclip  # Lazy import

    try:
        pyperclip.copy(text)
        log.info("copied_to_clipboard", length=len(text))
    except Exception as e:
        log.warning("clipboard_failed", error=str(e))
```

**Step 2: Test (integrated in next task)**

Will be tested in main loop.

**Step 3: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): add transcription and output handling"
```

---

## Task 9: Implement main recording loop

**Files:**
- Modify: `daemon_v2.py`

**Step 1: Add main loop implementation**

Update `main()` to replace the TODO with the actual loop:

```python
def main():
    args = parse_arguments()

    # Fast path: list devices
    if args.list_devices:
        try:
            list_audio_devices()
            return 0
        except Exception as e:
            print(f"Error listing devices: {e}")
            return 1

    log = configure_logging(args.debug, args.log_file)
    socket_path = get_socket_path(args.socket_path)
    state_manager = StateManager()

    setup_signal_handlers(state_manager)

    log.info("daemon_starting", version="2.0", socket_path=str(socket_path))

    # Load model (lazy imports happen here)
    try:
        model, device = load_model(args.cpu, log)
    except Exception as e:
        log.error("model_load_failed", error=str(e))
        return 1

    # Start socket server
    socket_server = UnixSocketServer(socket_path, state_manager, log)
    if not socket_server.start():
        return 1

    send_notification("Parakeet Ready", f"Model loaded on {device}", not args.no_notifications, log)

    log.info("daemon_ready", commands=["start", "stop", "toggle", "status", "shutdown"])

    # Main loop
    try:
        while not state_manager.is_shutdown_requested():
            # Wait for start command
            if not state_manager.wait_for_start():
                break

            log.info("recording_triggered")
            send_notification("Recording", "Listening...", not args.no_notifications, log)
            play_sound(log)

            # Record audio
            audio_data = record_audio(
                state_manager,
                sample_rate=16000,
                device_index=args.input_device,
                log=log,
            )

            if not audio_data or state_manager.is_shutdown_requested():
                state_manager.set_state(DaemonState.IDLE)
                continue

            # Save to temp file
            try:
                temp_path = save_audio_to_wav(audio_data)
            except Exception as e:
                log.error("audio_save_failed", error=str(e))
                state_manager.set_state(DaemonState.IDLE)
                continue

            # Transcribe
            state_manager.set_state(DaemonState.TRANSCRIBING)

            try:
                transcript = transcribe_audio(model, temp_path, device, log)
            except Exception as e:
                log.error("transcription_error", error=str(e))
                os.unlink(temp_path)
                state_manager.set_state(DaemonState.IDLE)
                continue
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

            if state_manager.is_shutdown_requested():
                break

            # Output
            play_sound(log)
            log.info("transcript", text=transcript)

            # Notification with preview
            preview = transcript[:80] + "..." if len(transcript) > 80 else transcript
            send_notification("Transcription Complete", preview, not args.no_notifications, log)

            # Handle output (auto-type or clipboard)
            handle_transcript_output(
                transcript,
                auto_type=not args.no_auto_type,
                use_clipboard=not args.no_clipboard,
                log=log,
            )

            # Return to idle
            state_manager.set_state(DaemonState.IDLE)
            log.info("ready_for_next_recording")

    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        socket_server.cleanup()
        log.info("daemon_stopped")

    return 0
```

**Step 2: Test full workflow**

Terminal 1: `python daemon_v2.py --cpu`
Expected: Daemon starts, loads model, shows "daemon_ready"

Terminal 2: `python parakeet-ctl.py toggle`
Expected: Recording starts

Terminal 2: Say something, then `python parakeet-ctl.py toggle`
Expected: Recording stops, transcription runs, transcript logged

**Step 3: Commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): implement main recording loop"
```

---

## Task 10: Final cleanup and testing

**Files:**
- Modify: `daemon_v2.py`
- Test: Manual integration testing

**Step 1: Add missing import for os.unlink**

At top of file, ensure `os` is imported (should already be there from earlier tasks).

**Step 2: Test all features**

Test checklist:
- [ ] `python daemon_v2.py --help` - shows help
- [ ] `python daemon_v2.py --list-devices` - lists devices quickly (no model load)
- [ ] `python daemon_v2.py --cpu` - starts daemon with CPU
- [ ] `python parakeet-ctl.py status` - returns idle
- [ ] `python parakeet-ctl.py toggle` - starts recording
- [ ] `python parakeet-ctl.py toggle` - stops and transcribes
- [ ] `python daemon_v2.py --cpu --debug` - shows debug logs
- [ ] `python daemon_v2.py --cpu --no-notifications` - no notifications
- [ ] `python daemon_v2.py --cpu --no-auto-type` - uses clipboard
- [ ] Ctrl+C - graceful shutdown

**Step 3: Verify structlog output**

Run with `--debug` and verify:
- INFO logs show: daemon_starting, model_loaded, recording_started, transcription_completed, etc.
- DEBUG logs show: notification_sent, command_received, etc.
- All logs have timestamps and structured fields

**Step 4: Final commit**

```bash
git add daemon_v2.py
git commit -m "feat(daemon-v2): complete rewrite with structlog - ready for testing"
```

---

## Success Criteria

- [ ] daemon_v2.py runs without errors
- [ ] All socket commands work (start, stop, toggle, status, shutdown)
- [ ] Audio recording and transcription work correctly
- [ ] Structlog produces clean, informative output
- [ ] `--list-devices` is fast (no heavy imports)
- [ ] `--debug` shows detailed logs
- [ ] Auto-typing and clipboard both work
- [ ] Notifications work (unless --no-notifications)
- [ ] Graceful shutdown on Ctrl+C
- [ ] All existing daemon.py features preserved

## Next Steps

After daemon_v2.py is working:
1. Update Makefile to add `daemon-v2` target
2. Test side-by-side with old daemon.py
3. When confident, replace daemon.py with daemon_v2.py
4. Update documentation
5. Clean up shell.nix, README, etc. (per BACKLOG)
