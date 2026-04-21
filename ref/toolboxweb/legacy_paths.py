"""Resolve paths relative to toolboxweb directory (independent of process cwd / PyInstaller)."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def toolboxweb_root() -> Path:
    return _ROOT


def static_path(*parts: str) -> Path:
    return _ROOT.joinpath("static", *parts)


def tools_path(filename: str) -> Path:
    return _ROOT / "tools" / filename


def ensure_temporary_dir() -> Path:
    d = _ROOT / "temporary"
    d.mkdir(parents=True, exist_ok=True)
    return d
