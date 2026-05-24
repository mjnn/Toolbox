#!/usr/bin/env python3
"""Fail if tool plugins import host-only modules or misuse MOS-only legacy adapters."""
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

# Keep tool plugins decoupled from host-only API modules and host config entrypoints.
FORBIDDEN_HOST_MODULES = re.compile(
    r"^\s*(?:from|import)\s+app\.api\.v1\.(admin_common|rbac|pagination)\b",
    re.MULTILINE,
)

FORBIDDEN_CORE_CONFIG = re.compile(
    r"^\s*(?:from|import)\s+app\.core\.config_simple\b",
    re.MULTILINE,
)

MOS_LEGACY_ADAPTER = re.compile(
    r"^\s*(?:from|import)\s+app\.services\.(mos_legacy_toolbox_adapter|legacy_toolbox_adapter)\b",
    re.MULTILINE,
)

FORBIDDEN_SECRET_KEY_ENV = re.compile(
    r"os\.getenv\(\s*['\"]SECRET_KEY['\"]",
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
        if FORBIDDEN_HOST_MODULES.search(text):
            print(
                f"Forbidden import in {py.relative_to(ROOT)}: tool plugins must not import host-only admin helpers",
                file=sys.stderr,
            )
            errors += 1
        if FORBIDDEN_CORE_CONFIG.search(text):
            print(
                f"Forbidden import in {py.relative_to(ROOT)}: tool plugins must not import app.core.config_simple "
                f"(use app.services.* for shared runtime helpers instead)",
                file=sys.stderr,
            )
            errors += 1

        rel = py.relative_to(PLUGINS)
        parts = rel.parts
        plugin_folder = parts[0] if parts else ""
        if plugin_folder != "mos_integration_toolbox" and MOS_LEGACY_ADAPTER.search(text):
            print(
                f"Forbidden import in {py.relative_to(ROOT)}: "
                f"app.services.mos_legacy_toolbox_adapter is MOS-only; do not import it from '{plugin_folder}'",
                file=sys.stderr,
            )
            errors += 1
        if FORBIDDEN_SECRET_KEY_ENV.search(text):
            print(
                f"Forbidden SECRET_KEY env access in {py.relative_to(ROOT)}: "
                f"tool plugins must not read SECRET_KEY directly (use app.services.secret_key helper)",
                file=sys.stderr,
            )
            errors += 1
    if errors:
        return 1
    print("OK: tool plugin boundary check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
