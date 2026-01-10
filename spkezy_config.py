"""Shared configuration loader for spkezy."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any


def get_config_path() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "spkezy" / "config.toml"
    return Path.home() / ".config" / "spkezy" / "config.toml"


def load_toml_config(log: Any | None = None) -> dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return {}

    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        if log:
            log.warning("config_read_failed", error=str(exc))
        return {}
