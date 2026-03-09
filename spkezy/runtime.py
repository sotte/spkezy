"""Shared runtime helpers for spkezy."""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any


def get_config_path() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "spkezy" / "config.toml"
    return Path.home() / ".config" / "spkezy" / "config.toml"


def get_data_dir() -> Path:
    """Get the data directory for stats storage."""
    data_home = os.getenv("XDG_DATA_HOME")
    if data_home:
        base = Path(data_home)
    else:
        base = Path.home() / ".local" / "share"
    return base / "spkezy"


def get_socket_path(override: str | None = None) -> Path:
    """Get the daemon socket path."""
    if override:
        return Path(override)

    runtime_dir = os.getenv("XDG_RUNTIME_DIR")
    if runtime_dir:
        return Path(runtime_dir) / "spkezy-daemon.sock"
    return Path("/tmp") / "spkezy-daemon.sock"


@lru_cache(maxsize=32)
def _load_toml_config_cached(path_str: str, mtime_ns: int | None) -> dict[str, Any]:
    path = Path(path_str)
    if mtime_ns is None or not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def clear_toml_config_cache() -> None:
    _load_toml_config_cached.cache_clear()


def load_toml_config(log: Any | None = None) -> dict[str, Any]:
    path = get_config_path()
    mtime_ns = path.stat().st_mtime_ns if path.exists() else None

    try:
        data = _load_toml_config_cached(str(path), mtime_ns)
        if log:
            event = "config_loaded" if mtime_ns is not None else "config_not_found"
            log.info(event, path=str(path))
        return data
    except Exception as exc:
        if log:
            log.warning("config_read_failed", path=str(path), error=str(exc))
        return {}
