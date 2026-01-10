"""Output configuration and helpers for transcripts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from spkezy_config import load_toml_config


@dataclass
class OutputConfig:
    post_clipboard_action: str = "none"


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

    return config


def is_wayland_session() -> bool:
    return bool(os.getenv("WAYLAND_DISPLAY"))
