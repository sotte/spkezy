#!/usr/bin/env python3
"""Parakeet TDT 0.6B v3 - Daemon Mode with Unix Socket IPC"""

import sys
import os
import io
import argparse
import logging
import time
import warnings
import threading
import wave
import tempfile
import socket
import json
import subprocess
from pathlib import Path
from enum import Enum
from contextlib import nullcontext
import signal
import atexit

# ============ Global shutdown ============
_shutdown_event = threading.Event()


# ============ Daemon state ============
class DaemonState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


_daemon_state = DaemonState.IDLE
_state_lock = threading.Lock()
_recording_start_event = threading.Event()
_recording_stop_event = threading.Event()


def _cleanup_handler():
    _shutdown_event.set()


atexit.register(_cleanup_handler)


def _signal_handler(signum, frame):
    _shutdown_event.set()


# Install signal handlers early (main thread)
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# Suppress KeyboardInterrupt traceback
def _no_kbi_traceback(exc_type, exc, tb):
    if exc_type is KeyboardInterrupt:
        return
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = _no_kbi_traceback

# ============ CLI ============
HELP_DESC = "Parakeet TDT 0.6B v3 daemon - keeps model loaded, listens on Unix socket for commands."
HELP_EPILOG = """Examples:
  python daemon.py
  python daemon.py --debug
  python daemon.py --cpu
  python daemon.py --socket-path /tmp/parakeet.sock
"""

parser = argparse.ArgumentParser(
    description=HELP_DESC,
    epilog=HELP_EPILOG,
    formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument(
    "-d",
    "--debug",
    action="store_true",
    help="Verbose diagnostics: device, timings, GPU memory (logs to file unless --log-file=-)",
)
parser.add_argument("--cpu", action="store_true", help="Force CPU inference")
parser.add_argument(
    "--no-clipboard", action="store_true", help="Do not copy transcript to clipboard"
)
parser.add_argument(
    "--log-file",
    default="transcriber.debug.log",
    help="Debug log file (use '-' for stderr)",
)
parser.add_argument(
    "--list-devices", action="store_true", help="List audio input devices and exit"
)
parser.add_argument(
    "--input-device", type=int, default=None, help="PyAudio input device index"
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
args = parser.parse_args()

# Determine socket path
if args.socket_path:
    SOCKET_PATH = Path(args.socket_path)
else:
    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        SOCKET_PATH = Path(runtime_dir) / "parakeet-daemon.sock"
    else:
        SOCKET_PATH = Path("/tmp") / "parakeet-daemon.sock"


# ============ Logging (truncate on --debug) ============
def configure_logging(debug: bool, log_file: str):
    if debug:
        if log_file != "-":
            try:
                if os.path.exists(log_file):
                    os.remove(log_file)
            except Exception:
                pass
            logging.basicConfig(
                filename=log_file, filemode="w", level=logging.DEBUG, force=True
            )
            print(f"Debug logs -> {log_file}")
        else:
            logging.basicConfig(level=logging.DEBUG, force=True)
    else:
        logging.basicConfig(level=logging.WARNING, force=True)


configure_logging(args.debug, args.log_file)
print("Starting...", flush=True)


def redirect_library_loggers_to_root_file():
    names = [
        "",
        "nemo_logger",
        "urllib3",
        "datasets",
        "matplotlib",
        "graphviz",
        "huggingface_hub",
        "transformers",
    ]
    for n in names:
        lg = logging.getLogger(n)
        for h in list(lg.handlers):
            lg.removeHandler(h)
        lg.propagate = True
        if args.debug:
            lg.setLevel(logging.DEBUG)


# ============ Fast path: list devices ============
if args.list_devices:
    try:
        import pyaudio

        pa = pyaudio.PyAudio()
        count = pa.get_device_count()
        print("Input devices:")
        for i in range(count):
            info = pa.get_device_info_by_index(i)
            if int(info.get("maxInputChannels", 0)) > 0:
                name = info.get("name", "unknown")
                rate = int(info.get("defaultSampleRate", 0))
                print(f"- id={i} name='{name}' rate={rate}Hz")
        pa.terminate()
    except Exception as e:
        print(f"Error listing devices: {e}")
    sys.exit(0)

# ============ Silencing helpers (normal mode) ============
old_stdout = None
stderr_fd = None
devnull_fd = None


def _silence_start():
    global old_stdout, stderr_fd, devnull_fd
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    stderr_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 2)


def _silence_stop():
    global old_stdout, stderr_fd, devnull_fd
    if old_stdout is not None:
        sys.stdout = old_stdout
        old_stdout = None
    if stderr_fd is not None:
        os.dup2(stderr_fd, 2)
        os.close(stderr_fd)
        stderr_fd = None
    if devnull_fd is not None:
        os.close(devnull_fd)
        devnull_fd = None


class SilentSTDERR:
    def __enter__(self):
        self.old_stderr = os.dup(2)
        self.devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(self.devnull, 2)
        return self

    def __exit__(self, *args):
        os.dup2(self.old_stderr, 2)
        os.close(self.old_stderr)
        os.close(self.devnull)


class SilentSTDOUT:
    def __enter__(self):
        self.old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        return self

    def __exit__(self, *args):
        sys.stdout = self.old_stdout


if not args.debug:
    os.environ.setdefault("NEMO_LOG_LEVEL", "ERROR")
    _silence_start()

# ============ Heavy imports ============
import nemo.collections.asr as nemo_asr
import pyaudio
import pyperclip
import torch

if not args.debug:
    _silence_stop()

warnings.filterwarnings("ignore")


# ============ Notifications ============
def notify(title: str, message: str, timeout: int = 2000, urgency: str = "normal"):
    """Send desktop notification via notify-send."""
    if args.no_notifications:
        return

    try:
        subprocess.run(
            ["notify-send", "-u", urgency, "-t", str(timeout), title, message],
            check=False,
            capture_output=True,
        )
        logging.debug(f"Notification sent: {title} - {message}")
    except Exception as e:
        logging.warning(f"Notification failed: {e}")


# ============ Spinner ============
def spinner_animation(stop_event, prefix, stream=None):
    stream = stream or sys.__stdout__
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    idx = 0
    try:
        while not stop_event.is_set() and not _shutdown_event.is_set():
            stream.write(f"\r{prefix} {chars[idx % len(chars)]}")
            stream.flush()
            idx += 1
            time.sleep(0.1)
    finally:
        stream.write("\033[2K\r")
        stream.flush()


# ============ Socket command handling ============
def wait_for_start_command():
    """Wait for 'start' command via event, return False if shutdown requested."""
    logging.info("Waiting for start command...")
    while not _shutdown_event.is_set():
        if _recording_start_event.wait(timeout=0.1):
            _recording_start_event.clear()
            logging.info("Start command received")
            return True
    return False


def record_audio_until_stop(sample_rate=16000, device_index=None):
    """Capture audio until stop event or shutdown."""
    global _daemon_state

    ctx = SilentSTDERR() if not args.debug else nullcontext()
    with ctx:
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
            logging.error(f"Audio error: {e}")
            print(f"❌ Audio error: {e}")
            try:
                p.terminate()
            except:
                pass
            return None

    frames = []
    logging.info("Recording started")
    print("🎤 Recording...", flush=True)
    notify("Recording", "Listening...")

    with _state_lock:
        _daemon_state = DaemonState.RECORDING

    ctx = SilentSTDERR() if not args.debug else nullcontext()
    with ctx:
        while not _shutdown_event.is_set():
            # Stop on stop event
            if _recording_stop_event.is_set():
                _recording_stop_event.clear()
                logging.info("Stop command received")
                break
            try:
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            except:
                continue

        stream.stop_stream()
        stream.close()
        p.terminate()

    logging.info(f"Recording stopped, captured {len(frames)} frames")
    return b"".join(frames) if frames else None


def save_audio(audio_data, filename, sample_rate=16000):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)


class _silence_context:
    def __enter__(self):
        _silence_start()
        return self

    def __exit__(self, *exc):
        _silence_stop()
        return False


# ============ Socket Server ============
def handle_client_command(client_socket):
    """Handle incoming command from client."""
    global _daemon_state

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

        logging.info(f"Received command: {cmd}")

        response = {}

        if cmd == "start":
            with _state_lock:
                if _daemon_state == DaemonState.IDLE:
                    _recording_start_event.set()
                    response = {"status": "ok", "state": "recording"}
                else:
                    response = {
                        "status": "error",
                        "message": f"Cannot start, currently {_daemon_state.value}",
                    }

        elif cmd == "stop":
            with _state_lock:
                if _daemon_state == DaemonState.RECORDING:
                    _recording_stop_event.set()
                    response = {"status": "ok", "state": "transcribing"}
                else:
                    response = {
                        "status": "error",
                        "message": f"Cannot stop, currently {_daemon_state.value}",
                    }

        elif cmd == "toggle":
            with _state_lock:
                if _daemon_state == DaemonState.IDLE:
                    _recording_start_event.set()
                    response = {"status": "ok", "action": "started", "state": "recording"}
                    logging.info("Toggle: starting recording")
                elif _daemon_state == DaemonState.RECORDING:
                    _recording_stop_event.set()
                    response = {"status": "ok", "action": "stopped", "state": "transcribing"}
                    logging.info("Toggle: stopping recording")
                else:
                    response = {
                        "status": "error",
                        "message": f"Cannot toggle while {_daemon_state.value}",
                    }

        elif cmd == "status":
            with _state_lock:
                response = {"status": "ok", "state": _daemon_state.value}

        elif cmd == "shutdown":
            logging.info("Shutdown command received")
            _shutdown_event.set()
            response = {"status": "ok", "message": "shutting down"}

        else:
            response = {"status": "error", "message": f"Unknown command: {cmd}"}

        client_socket.sendall((json.dumps(response) + "\n").encode())

    except Exception as e:
        logging.error(f"Error handling command: {e}")
        try:
            error_response = {"status": "error", "message": str(e)}
            client_socket.sendall((json.dumps(error_response) + "\n").encode())
        except:
            pass
    finally:
        client_socket.close()


def socket_server_thread(sock):
    """Accept connections and handle commands in separate threads."""
    logging.info(f"Socket server listening on {SOCKET_PATH}")

    while not _shutdown_event.is_set():
        try:
            sock.settimeout(0.5)
            client_sock, _ = sock.accept()
            # Handle each command in a separate thread
            threading.Thread(
                target=handle_client_command, args=(client_sock,), daemon=True
            ).start()
        except socket.timeout:
            continue
        except Exception as e:
            if not _shutdown_event.is_set():
                logging.error(f"Socket server error: {e}")
            break

    logging.info("Socket server stopped")


def setup_socket_server():
    """Set up Unix socket server."""
    # Clean up stale socket
    if SOCKET_PATH.exists():
        try:
            # Try to connect - if it works, daemon is already running
            test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            test_sock.connect(str(SOCKET_PATH))
            test_sock.close()
            print(f"❌ Daemon already running at {SOCKET_PATH}")
            sys.exit(1)
        except ConnectionRefusedError:
            # Stale socket, remove it
            SOCKET_PATH.unlink()
            logging.info(f"Removed stale socket at {SOCKET_PATH}")

    # Create socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(SOCKET_PATH))
    sock.listen(5)

    logging.info(f"Socket server created at {SOCKET_PATH}")

    # Start server thread
    server_thread = threading.Thread(
        target=socket_server_thread, args=(sock,), daemon=True
    )
    server_thread.start()

    return sock


# ============ Main ============
def main():
    if args.debug and args.log_file != "-":
        redirect_library_loggers_to_root_file()

    # Spinner: Loading model
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(
        target=spinner_animation,
        args=(stop_spinner, "⏳ Loading model"),
        kwargs={"stream": sys.__stdout__},
        daemon=True,
    )
    spinner_thread.start()

    # Load model
    load_ctx = nullcontext() if args.debug else _silence_context()
    t_load0 = time.perf_counter()
    try:
        with load_ctx:
            model = nemo_asr.models.ASRModel.from_pretrained(
                "nvidia/parakeet-tdt-0.6b-v3"
            )
    except Exception as e:
        stop_spinner.set()
        spinner_thread.join()
        print(f"❌ Error: {e}")
        return 1
    finally:
        t_load1 = time.perf_counter()
        stop_spinner.set()
        spinner_thread.join()

    if _shutdown_event.is_set():
        return 0

    # Device
    use_cuda = torch.cuda.is_available() and not args.cpu
    device = "cuda" if use_cuda else "cpu"
    model.to(device)
    model.eval()

    # Set up socket server
    sock = setup_socket_server()

    # Notify model loaded
    notify("Parakeet Ready", f"Model loaded on {device}, ready for dictation")

    # Header
    print("🚀 PARAKEET TDT 0.6B V3 - DAEMON MODE")
    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    print("=" * 60)
    print(f"📡 Listening on: {SOCKET_PATH}")
    print("   Send 'start' to begin recording")
    print("   Send 'stop' to transcribe")
    print("   Ctrl+C to exit")
    print("=" * 60 + "\n")

    if args.debug:
        print(f"Model device: {next(model.parameters()).device}")
        if use_cuda:
            cap = torch.cuda.get_device_capability()
            print(f"CUDA capability: {cap[0]}.{cap[1]}")
            print(
                f"GPU alloc (MiB) after load: {torch.cuda.memory_allocated() / 1024**2:.2f}"
            )
        print(f"Model load time: {t_load1 - t_load0:.3f}s")

    global _daemon_state

    try:
        while not _shutdown_event.is_set():
            # Wait for start command
            if not wait_for_start_command():
                break

            sr = 16000
            t_rec0 = time.perf_counter()
            audio_data = record_audio_until_stop(
                sample_rate=sr, device_index=args.input_device
            )
            t_rec1 = time.perf_counter()

            if not audio_data or _shutdown_event.is_set():
                with _state_lock:
                    _daemon_state = DaemonState.IDLE
                continue

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                save_audio(audio_data, tmp.name, sample_rate=sr)
                temp_path = tmp.name

            # Update state to transcribing
            with _state_lock:
                _daemon_state = DaemonState.TRANSCRIBING

            # Spinner: Generating...
            gen_stop = threading.Event()
            gen_spinner = threading.Thread(
                target=spinner_animation,
                args=(gen_stop, "🤖 Transcribing..."),
                kwargs={"stream": sys.__stdout__},
                daemon=True,
            )
            gen_spinner.start()

            infer_ctx = nullcontext() if args.debug else _silence_context()
            t_inf0 = time.perf_counter()
            try:
                with infer_ctx:
                    result = model.transcribe([temp_path], verbose=False)
                if isinstance(result, list) and len(result) > 0:
                    first = result[0]
                    transcript = getattr(
                        first, "text", first if isinstance(first, str) else str(first)
                    )
                else:
                    transcript = str(result)
            except Exception as e:
                gen_stop.set()
                gen_spinner.join()
                logging.error(f"Transcription error: {e}")
                print(f"❌ Error: {e}")
                try:
                    os.unlink(temp_path)
                except:
                    pass
                # Return to IDLE state
                with _state_lock:
                    _daemon_state = DaemonState.IDLE
                continue
            finally:
                t_inf1 = time.perf_counter()
                gen_stop.set()
                gen_spinner.join()

            if _shutdown_event.is_set():
                try:
                    os.unlink(temp_path)
                except:
                    pass
                break

            print(f"📝 {transcript}\n")
            logging.info(f"Transcription: {transcript}")

            # Show notification with preview
            preview = transcript[:80] + "..." if len(transcript) > 80 else transcript
            notify("Transcription Complete", preview)

            if not args.no_clipboard:
                try:
                    pyperclip.copy(transcript)
                    logging.info("Copied to clipboard")
                except Exception as e:
                    logging.warning(f"Clipboard error: {e}")
                    if args.debug:
                        print(f"Clipboard warning: {e}")

            if args.debug:
                secs = len(audio_data) / (2 * sr)
                print(
                    f"Audio length: {secs:.2f}s | Record: {t_rec1 - t_rec0:.3f}s | Infer: {t_inf1 - t_inf0:.3f}s"
                )
                if use_cuda:
                    print(
                        f"GPU alloc (MiB) after infer: {torch.cuda.memory_allocated() / 1024**2:.2f}"
                    )

            try:
                os.unlink(temp_path)
            except:
                pass

            # Return to IDLE state
            with _state_lock:
                _daemon_state = DaemonState.IDLE
            logging.info("Ready for next recording")

        # Cleanup
        sock.close()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        logging.info("Socket cleaned up")

        return 0

    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    try:
        code = main()
        print("\n👋 Goodbye!", flush=True)
        sys.exit(code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!", flush=True)
        sys.exit(130)
