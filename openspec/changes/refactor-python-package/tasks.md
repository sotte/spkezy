## 1. Implementation

- [x] 1.1 Create `spkezy/` package directory and empty `spkezy/__init__.py`
- [x] 1.2 Move client CLI logic from `spkezy.py` into `spkezy/__main__.py`
- [x] 1.3 Move daemon loop from `spkezy_daemon.py` into `spkezy/daemon.py`
- [x] 1.4 Extract Unix socket server + client send into `spkezy/io.py`
- [x] 1.5 Extract XDG config/data + socket path helpers into `spkezy/runtime.py`
- [x] 1.6 Move `spkezy_output.py` → `spkezy/output.py` and update imports
- [x] 1.7 Move `spkezy_postprocess.py` → `spkezy/postprocess.py` and update imports
- [x] 1.8 Move `spkezy_stats.py` → `spkezy/stats.py` and update imports
- [x] 1.9 Update or remove root-level `spkezy.py`/`spkezy_daemon.py` wrappers
- [x] 1.10 Update `pyproject.toml` scripts to use `spkezy.__main__` entrypoints
- [x] 1.11 Update `pyproject.toml` build includes to package directory + assets
- [x] 1.12 Update `pyproject.toml` lint/typecheck paths to point at `spkezy/`
- [x] 1.13 Update `README.md` usage and command examples
