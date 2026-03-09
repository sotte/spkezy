"""Audio input configuration and device selection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spkezy.runtime import load_toml_config

DEFAULT_INPUT_DEVICE = "auto"
SYSDEFAULT_INPUT_DEVICE = "sysdefault"
PREFERRED_INPUT_SAMPLE_RATE = 16000
_COMMON_SAMPLE_RATES = (48000, 44100, 32000, 24000, 22050, 16000, 11025, 8000)


@dataclass
class AudioConfig:
    input_device: str | int = DEFAULT_INPUT_DEVICE


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
        raise ValueError("Invalid audio.input_device value; must be a device name or index.")
    if isinstance(input_device, int):
        config.input_device = input_device
        return config
    if isinstance(input_device, str) and input_device.strip():
        config.input_device = input_device.strip()
        return config

    raise ValueError("Invalid audio.input_device value; must be a device name or index.")


def resolve_input_device_index(pa: Any, device_spec: str | int | None) -> int:
    input_devices = [
        pa.get_device_info_by_index(i)
        for i in range(pa.get_device_count())
        if int(pa.get_device_info_by_index(i).get("maxInputChannels", 0)) > 0
    ]
    if not input_devices:
        raise ValueError("No input audio devices available.")

    default_index = int(pa.get_default_input_device_info()["index"])

    if device_spec is None:
        return default_index

    if isinstance(device_spec, str):
        stripped = device_spec.strip()
        if not stripped:
            raise ValueError("Audio input device cannot be blank.")
        if stripped.isdecimal():
            return resolve_input_device_index(pa, int(stripped))

        normalized = _normalize_device_name(stripped)
        if normalized == "default":
            return default_index
        if normalized == "auto":
            return _resolve_auto_input_device_index(input_devices, default_index)

        exact_match = _find_input_device_index_by_name(input_devices, stripped)
        if exact_match is not None:
            return exact_match

        available_names = ", ".join(
            repr(str(info.get("name", "unknown"))) for info in input_devices
        )
        raise ValueError(
            f"Audio input device '{device_spec}' was not found. "
            "Use an exact device name or index. "
            f"Available devices: {available_names}"
        )

    if isinstance(device_spec, int):
        try:
            info = pa.get_device_info_by_index(device_spec)
        except Exception as exc:
            raise ValueError(f"Audio input device index {device_spec} was not found.") from exc
        if int(info.get("maxInputChannels", 0)) <= 0:
            raise ValueError(f"Audio device index {device_spec} does not support audio input.")
        return device_spec

    raise ValueError("Audio input device must be a device name or index.")


def choose_input_sample_rate(
    pa: Any,
    device_index: int,
    input_format: Any,
    preferred_sample_rate: int = PREFERRED_INPUT_SAMPLE_RATE,
) -> int:
    info = pa.get_device_info_by_index(device_index)
    candidates: list[int] = [preferred_sample_rate]

    default_rate = int(round(float(info.get("defaultSampleRate", 0))))
    if default_rate > 0:
        candidates.append(default_rate)

    for rate in _COMMON_SAMPLE_RATES:
        if rate not in candidates:
            candidates.append(rate)

    for rate in candidates:
        try:
            supported = pa.is_format_supported(
                rate,
                input_device=device_index,
                input_channels=1,
                input_format=input_format,
            )
        except Exception:
            supported = False
        if supported:
            return rate

    device_name = str(info.get("name", "unknown"))
    raise ValueError(f"No supported mono 16-bit capture sample rate found for '{device_name}'.")


def validate_audio_input_stream(
    pa: Any,
    device_index: int,
    sample_rate: int,
    input_format: Any,
    frames_per_buffer: int = 1024,
) -> None:
    stream = None
    try:
        stream = pa.open(
            format=input_format,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=frames_per_buffer,
        )
    except Exception as exc:
        device_name = str(pa.get_device_info_by_index(device_index).get("name", "unknown"))
        raise ValueError(
            f"Unable to open audio input '{device_name}' at {sample_rate}Hz: {exc}"
        ) from exc
    finally:
        if stream is not None:
            stream.close()


def resolve_audio_input(
    device_spec: str | int | None,
    preferred_sample_rate: int = PREFERRED_INPUT_SAMPLE_RATE,
    log: Any | None = None,
) -> tuple[int, int, str]:
    import pyaudio

    pa = pyaudio.PyAudio()
    try:
        device_index = resolve_input_device_index(pa, device_spec)
        device_info = pa.get_device_info_by_index(device_index)
        sample_rate = choose_input_sample_rate(
            pa,
            device_index=device_index,
            input_format=pyaudio.paInt16,
            preferred_sample_rate=preferred_sample_rate,
        )
        validate_audio_input_stream(
            pa,
            device_index=device_index,
            sample_rate=sample_rate,
            input_format=pyaudio.paInt16,
        )
        device_name = str(device_info.get("name", "unknown"))
        if log:
            log.info(
                "audio_input_selected",
                input_device=device_name,
                input_device_index=device_index,
                sample_rate=sample_rate,
                preferred_sample_rate=preferred_sample_rate,
            )
        return device_index, sample_rate, device_name
    finally:
        pa.terminate()


def _resolve_auto_input_device_index(
    input_devices: list[dict[str, Any]], default_index: int
) -> int:
    sysdefault_index = _find_input_device_index_by_name(input_devices, SYSDEFAULT_INPUT_DEVICE)
    if sysdefault_index is not None:
        return sysdefault_index
    return default_index


def _find_input_device_index_by_name(
    input_devices: list[dict[str, Any]], device_name: str
) -> int | None:
    normalized_target = _normalize_device_name(device_name)
    for info in input_devices:
        if _normalize_device_name(str(info.get("name", ""))) == normalized_target:
            return int(info["index"])
    return None


def _normalize_device_name(name: str) -> str:
    return " ".join(name.casefold().split())
