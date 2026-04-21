#!/usr/bin/env python3
"""Validate backend tool manifest JSON files against contracts/tool.manifest.schema.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "tool.manifest.schema.json"


def main() -> int:
    try:
        import jsonschema
    except ImportError:
        print("Install jsonschema: pip install jsonschema", file=sys.stderr)
        return 1

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    manifest_dir = ROOT / "backend" / "app" / "tools" / "plugins"
    paths = sorted(manifest_dir.glob("*/tool.manifest.json"))
    errors = 0
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for e in validator.iter_errors(data):
            errors += 1
            print(f"{path.relative_to(ROOT)}: {e.message}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK: validated {len(paths)} manifest(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
