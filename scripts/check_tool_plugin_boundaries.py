#!/usr/bin/env python3
"""Fail if tool plugin routes import host-only admin modules (keep tools decoupled from global admin)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "backend" / "app" / "tools" / "plugins"

FORBIDDEN = re.compile(
    r"^\s*(?:from|import)\s+app\.api\.v1\.admin\b",
    re.MULTILINE,
)


def main() -> int:
    errors = 0
    for py in sorted(PLUGINS.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        text = py.read_text(encoding="utf-8")
        if FORBIDDEN.search(text):
            print(f"Forbidden import in {py.relative_to(ROOT)}: do not import app.api.v1.admin from tool plugins", file=sys.stderr)
            errors += 1
    if errors:
        return 1
    print("OK: tool plugin boundary check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
