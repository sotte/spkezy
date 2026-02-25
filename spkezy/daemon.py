#!/usr/bin/env python3
"""spkezy - Automatic Speech Recognition Daemon"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
import warnings
import wave
from pathlib import Path
from typing import Any

import structlog

from spkezy.io import DaemonState, StateManager, UnixSocketServer
from spkezy.output import is_autotype_supported, load_output_config
from spkezy.postprocess import load_postprocess_config, postprocess_transcript
from spkezy.runtime import get_socket_path
from spkezy.stats import record_stats


########################################################################################
# CLI Arguments
def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="spkezy daemon - keeps ASR model loaded, listens on Unix socket for commands.",
        epilog="""Examples:
  spkezy-daemon
  spkezy-daemon --debug
  spkezy-daemon --cpu
  spkezy-daemon --socket-path /tmp/spk.sock
""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Verbose diagnostics: device, timings, GPU memory",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU inference",
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
        help=(
            "Unix socket path "
            "(default: $XDG_RUNTIME_DIR/spkezy-daemon.sock or /tmp/spkezy-daemon.sock)"
        ),
    )
    parser.add_argument(
        "--no-notifications",
        action="store_true",
        help="Disable desktop notifications",
    )
    return parser.parse_args()


########################################################################################
# Logging Configuration
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


########################################################################################
# Notifications & Audio Feedback
def _escape_applescript_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def get_notification_command(title: str, message: str) -> list[str]:
    if sys.platform == "darwin":
        escaped_title = _escape_applescript_string(title)
        escaped_message = _escape_applescript_string(message)
        script = f'display notification "{escaped_message}" with title "{escaped_title}"'
        return ["osascript", "-e", script]
    return ["notify-send", "-u", "normal", "-t", "2000", title, message]


def get_sound_command(sound_file: Path) -> list[str]:
    player = "afplay" if sys.platform == "darwin" else "paplay"
    return [player, str(sound_file)]


def get_autotype_command(text: str, delay_ms: int) -> list[str]:
    if sys.platform == "darwin":
        escaped_text = _escape_applescript_string(text)
        script = f'tell application "System Events" to keystroke "{escaped_text}"'
        return ["osascript", "-e", script]

    command = ["wtype"]
    if delay_ms > 0:
        command.extend(["-d", str(delay_ms)])
    command.append(text)
    return command


def send_notification(title: str, message: str, enabled: bool = True, log=None):
    """Send desktop notification using platform-specific backend."""
    if not enabled:
        return

    try:
        command = get_notification_command(title, message)
        subprocess.run(
            command,
            check=False,
            capture_output=True,
        )
        if log:
            log.debug("notification_sent", title=title, message=message)
    except Exception as e:
        if log:
            log.warning("notification_failed", error=str(e))


def play_sound(log=None):
    """Play sound.mp3 via platform-specific command (non-blocking)."""
    try:
        sound_file = Path(__file__).parent / "sound.mp3"
        if not sound_file.exists():
            return

        command = get_sound_command(sound_file)
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        if log:
            log.debug("sound_playback_failed", error=str(e))


def auto_type_text(text: str, delay_ms: int, log=None):
    """Auto-type text using platform-specific backend."""
    try:
        command = get_autotype_command(text, delay_ms)
        subprocess.run(
            command,
            check=True,
            capture_output=True,
        )
        if log:
            log.info("auto_typed", length=len(text), delay_ms=delay_ms)
    except FileNotFoundError:
        if log:
            tool_name = "osascript" if sys.platform == "darwin" else "wtype"
            log.warning("autotype_tool_not_found", tool=tool_name)
        raise
    except subprocess.CalledProcessError as e:
        if log:
            log.warning("wtype_failed", exit_code=e.returncode, stderr=e.stderr.decode())
        raise


def _mps_available(torch_module: Any) -> bool:
    backends = getattr(torch_module, "backends", None)
    if backends is None:
        return False
    mps_backend = getattr(backends, "mps", None)
    if mps_backend is None:
        return False
    checker = getattr(mps_backend, "is_available", None)
    if checker is None:
        return False
    return bool(checker())


def select_inference_device(torch_module: Any, force_cpu: bool, log: Any) -> str:
    if force_cpu:
        log.info("device_detected", device="cpu", note="Forced CPU mode (--cpu flag)")
        return "cpu"

    if torch_module.cuda.is_available():
        gpu_name = torch_module.cuda.get_device_name(0)
        cap = torch_module.cuda.get_device_capability()
        log.info(
            "device_detected",
            device="cuda",
            gpu=gpu_name,
            cuda_capability=f"{cap[0]}.{cap[1]}",
        )
        return "cuda"

    if _mps_available(torch_module):
        log.info("device_detected", device="mps", note="Using Apple Silicon GPU (MPS)")
        return "mps"

    log.info("device_detected", device="cpu", note="No CUDA or MPS GPU detected")
    return "cpu"


########################################################################################
# Model Loading
def load_model(force_cpu: bool, log: Any) -> tuple[Any, str]:
    """Load NeMo ASR model with lazy imports."""
    log.info("model_loading_start", model="nvidia/parakeet-tdt-0.6b-v3")

    # Suppress warnings
    warnings.filterwarnings("ignore")

    # Lazy imports - only load when actually starting daemon
    import nemo.collections.asr as nemo_asr
    import torch

    # Detect device
    device = select_inference_device(torch, force_cpu, log)

    # Load model
    t_start = time.perf_counter()
    model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3")
    # Move to device; if accelerator transfer fails, fall back to CPU.
    try:
        model.to(device)
    except Exception as exc:
        if device != "cpu":
            log.warning("device_fallback_to_cpu", from_device=device, error=str(exc))
            device = "cpu"
            model.to(device)
        else:
            raise
    model.eval()
    t_end = time.perf_counter()

    log.info("model_loaded", device=device, load_time_seconds=round(t_end - t_start, 1))

    return model, device


########################################################################################
# Audio Recording
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


########################################################################################
# Transcription
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
        log.info(
            "transcription_completed",
            length=len(transcript),
            time_seconds=round(t_end - t_start, 3),
        )

        return transcript

    except Exception as e:
        log.error("transcription_failed", error=str(e))
        raise


def handle_transcript_output(
    transcript: str,
    post_clipboard_action: str,
    autotype_delay_ms: int,
    log,
):
    """Handle transcript output: copy to clipboard, then optional action."""
    copy_to_clipboard(transcript, log)

    if post_clipboard_action == "none":
        return

    if not is_autotype_supported():
        log.warning("output_action_unsupported", action=post_clipboard_action)
        return

    if post_clipboard_action == "autotype":
        try:
            auto_type_text(transcript, autotype_delay_ms, log)
        except Exception as e:
            log.warning("auto_type_failed", error=str(e))
        return

    log.warning("output_action_invalid", action=post_clipboard_action)


def copy_to_clipboard(text: str, log):
    """Copy text to clipboard using pyperclip."""
    import pyperclip  # Lazy import

    try:
        pyperclip.copy(text)
        log.info("copied_to_clipboard", length=len(text))
    except Exception as e:
        log.warning("clipboard_failed", error=str(e))


########################################################################################
# MAIN
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
    postprocess_config = load_postprocess_config(log)
    try:
        output_config = load_output_config(log)
    except ValueError as exc:
        log.error("output_config_invalid", error=str(exc))
        return 1

    setup_signal_handlers(state_manager)

    log.info("daemon_starting", version="2.0", socket_path=str(socket_path))

    send_notification(
        "🥃 spkezy - Loading Model",
        "Loading speech model...",
        not args.no_notifications,
        log,
    )

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

    send_notification(
        "🥃 spkezy - Ready",
        f"Model loaded on {device}",
        not args.no_notifications,
        log,
    )

    log.info("daemon_ready", commands=["start", "stop", "toggle", "status", "shutdown"])

    # Main loop
    try:
        while not state_manager.is_shutdown_requested():
            # Wait for start command
            if not state_manager.wait_for_start():
                break

            log.info("recording_triggered")
            send_notification(
                "🥃 spkezy - Recording",
                "Listening...",
                not args.no_notifications,
                log,
            )
            play_sound(log)

            # Track recording start time for stats
            recording_start_time = time.perf_counter()

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

            # Calculate recording duration for stats
            recording_duration_ms = int((time.perf_counter() - recording_start_time) * 1000)

            # Notify user that transcription is starting
            send_notification(
                "🥃 spkezy - Transcribing",
                "Processing audio",
                not args.no_notifications,
                log,
            )
            play_sound(log)

            # Save to temp file
            try:
                temp_path = save_audio_to_wav(audio_data)
            except Exception as e:
                log.error("audio_save_failed", error=str(e))
                state_manager.set_state(DaemonState.IDLE)
                continue

            # Transcribe
            state_manager.set_state(DaemonState.TRANSCRIBING)

            # Track transcription start time for stats
            transcription_start_time = time.perf_counter()

            try:
                transcript = transcribe_audio(model, temp_path, device, log)
                transcript = postprocess_transcript(transcript, postprocess_config, log)
                transcription_duration_ms = int(
                    (time.perf_counter() - transcription_start_time) * 1000
                )
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
            send_notification(
                "🥃 spkezy - Transcription Complete",
                preview,
                not args.no_notifications,
                log,
            )

            # Handle output (auto-type or clipboard)
            handle_transcript_output(
                transcript,
                post_clipboard_action=output_config.post_clipboard_action,
                autotype_delay_ms=output_config.autotype_delay_ms,
                log=log,
            )

            # Record stats
            try:
                record_stats(
                    recording_duration_ms=recording_duration_ms,
                    transcription_duration_ms=transcription_duration_ms,
                    transcript=transcript,
                    device=device,
                )
            except Exception as e:
                log.warning("stats_recording_failed", error=str(e))

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


if __name__ == "__main__":
    sys.exit(main())
