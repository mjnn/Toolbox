#!/usr/bin/env bash
set -euo pipefail

INVENTORY_DIR="${1:-/srv/apps/_inventory}"
WHITELIST_FILE="${INVENTORY_DIR}/stale-whitelist.txt"

mkdir -p "${INVENTORY_DIR}"
touch "${WHITELIST_FILE}"

python3 - "${INVENTORY_DIR}" "${WHITELIST_FILE}" <<'PY'
import subprocess
import sys
from pathlib import Path

inventory = Path(sys.argv[1])
whitelist_file = Path(sys.argv[2])
whitelist = {line.strip() for line in whitelist_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")}

cmd = ["docker", "ps", "-a", "--filter", "status=exited", "--filter", "status=created", "--format", "{{.Names}}"]
res = subprocess.run(cmd, check=True, capture_output=True, text=True)
names = [n.strip() for n in res.stdout.splitlines() if n.strip()]

keep = [n for n in names if n in whitelist]
remove = [n for n in names if n not in whitelist]

(inventory / "stale-before.txt").write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
(inventory / "stale-keep.txt").write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
(inventory / "stale-remove.txt").write_text("\n".join(remove) + ("\n" if remove else ""), encoding="utf-8")

if remove:
    subprocess.run(["docker", "rm", *remove], check=True)

(inventory / "stale-removed.txt").write_text("\n".join(remove) + ("\n" if remove else ""), encoding="utf-8")
post = subprocess.run(cmd, check=True, capture_output=True, text=True)
remaining = [n.strip() for n in post.stdout.splitlines() if n.strip()]
(inventory / "stale-after.txt").write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")

print(f"stale_total={len(names)}")
print(f"keep_total={len(keep)}")
print(f"remove_total={len(remove)}")
print(f"remaining_total={len(remaining)}")
print("remaining=" + (",".join(remaining) if remaining else "(none)"))
PY
