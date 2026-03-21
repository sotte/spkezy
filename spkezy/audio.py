"""Audio input configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spkezy.runtime import load_toml_config

DEFAULT_INPUT_DEVICE = "auto"
SAMPLE_RATE = 16000


@dataclass
class AudioConfig:
    input_device: str = DEFAULT_INPUT_DEVICE


def load_audio_config(log: Any | None = None, data: dict[str, Any] | None = None) -> AudioConfig:
    config_data = data if data is not None else load_toml_config(log)
    section = config_data.get("audio", {})
    config = AudioConfig()

    if not isinstance(section, dict):
        return config

    input_device = section.get("input_device")
    if input_device is None:
        return config
    if isinstance(input_device, bool):
        raise ValueError("Invalid audio.input_device value; must be a device name or 'auto'.")
    if isinstance(input_device, int):
        if log:
            log.warning(
                "audio_config_int_device_deprecated",
                msg="Numeric device indices are no longer supported with PipeWire capture. "
                "Using 'auto' instead. Set input_device to a PipeWire source name or 'auto'.",
                value=input_device,
            )
        return config
    if isinstance(input_device, str) and input_device.strip():
        config.input_device = input_device.strip()
        return config

    raise ValueError("Invalid audio.input_device value; must be a device name or 'auto'.")


def resolve_capture_target(device_spec: str, log: Any | None = None) -> str | None:
    """Resolve a config device spec to a pw-record --target value.

    Returns None for system default (auto/default), or a source name string.
    """
    normalized = " ".join(device_spec.casefold().split())
    if normalized in ("auto", "default"):
        if log:
            log.info("audio_input_mode", mode="system-default")
        return None

    # Explicit PipeWire source name
    if log:
        log.info("audio_input_mode", mode="explicit", target=device_spec)
    return device_spec
