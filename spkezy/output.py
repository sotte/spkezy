"""Output configuration and helpers for transcripts."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

from spkezy.runtime import load_toml_config


@dataclass
class OutputConfig:
    post_clipboard_action: str = "none"
    autotype_delay_ms: int = 0


def load_output_config(log: Any | None = None) -> OutputConfig:
    data = load_toml_config(log)
    section = data.get("output", {})
    config = OutputConfig()

    if isinstance(section, dict):
        action = section.get("post_clipboard_action")
        if isinstance(action, str) and action.strip():
            normalized = action.strip().lower()
            if normalized in {"none", "autotype"}:
                config.post_clipboard_action = normalized
            else:
                raise ValueError(
                    f"Invalid post_clipboard_action '{action}'. Use 'none' or 'autotype'."
                )
        delay_value = section.get("autotype_delay_ms")
        if delay_value is not None:
            if isinstance(delay_value, bool) or not isinstance(delay_value, int):
                raise ValueError("Invalid autotype_delay_ms value; must be a non-negative integer.")
            if delay_value < 0:
                raise ValueError("Invalid autotype_delay_ms value; must be a non-negative integer.")
            config.autotype_delay_ms = delay_value

    return config


def is_wayland_session() -> bool:
    return bool(os.getenv("WAYLAND_DISPLAY"))


def is_autotype_supported() -> bool:
    if sys.platform == "darwin":
        return True
    return is_wayland_session()
