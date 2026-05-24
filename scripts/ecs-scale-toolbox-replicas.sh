#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <replica-count>"
  echo "Example: $0 2"
  exit 1
fi

TARGET_REPLICAS="$1"
if ! [[ "${TARGET_REPLICAS}" =~ ^[0-9]+$ ]]; then
  echo "Replica count must be a non-negative integer"
  exit 1
fi

if [[ "${TARGET_REPLICAS}" -lt 1 ]]; then
  echo "At least one replica is required"
  exit 1
fi

BASE_CONTAINER="tool-box-public"
BASE_PORT=3000

BASE_IMAGE="$(docker inspect "${BASE_CONTAINER}" --format '{{.Config.Image}}')"
BASE_DATABASE_URL="$(docker inspect "${BASE_CONTAINER}" --format '{{range .Config.Env}}{{println .}}{{end}}' | awk -F= '/^DATABASE_URL=/{print substr($0,14)}')"
BASE_CORS="$(docker inspect "${BASE_CONTAINER}" --format '{{range .Config.Env}}{{println .}}{{end}}' | awk -F= '/^BACKEND_CORS_ORIGINS=/{print substr($0,22)}')"
BASE_EXTERNAL_IP="$(docker inspect "${BASE_CONTAINER}" --format '{{range .Config.Env}}{{println .}}{{end}}' | awk -F= '/^TOOLBOX_EXTERNAL_PUBLIC_IP=/{print substr($0,28)}')"

if [[ -z "${BASE_DATABASE_URL}" ]]; then
  echo "Cannot read DATABASE_URL from ${BASE_CONTAINER}"
  exit 1
fi

for i in $(seq 2 "${TARGET_REPLICAS}"); do
  NAME="tool-box-public-r${i}"
  HOST_PORT=$((BASE_PORT + i - 1))
  if docker ps -a --format '{{.Names}}' | grep -Eq "^${NAME}$"; then
    echo "Replica exists: ${NAME} (skip)"
    continue
  fi

  echo "Starting replica ${NAME} on port ${HOST_PORT}"
  docker run -d \
    --name "${NAME}" \
    --restart unless-stopped \
    -p "${HOST_PORT}:3000" \
    -e "DATABASE_URL=${BASE_DATABASE_URL}" \
    -e "TOOLBOX_VISIBLE_TOOL_KEYS=service-id-registry" \
    -e "TOOLBOX_WORKERS=1" \
    -e "BACKEND_CORS_ORIGINS=${BASE_CORS}" \
    -e "TOOLBOX_EXTERNAL_PUBLIC_IP=${BASE_EXTERNAL_IP}" \
    "${BASE_IMAGE}"
done

echo
echo "Current toolbox replicas:"
docker ps --filter name=tool-box-public --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

UPSTREAM_CONF="/etc/nginx/conf.d/toolbox-upstream.conf"
if [[ -f "${UPSTREAM_CONF}" ]]; then
  echo
  echo "Updating nginx upstream pool: ${UPSTREAM_CONF}"
  sudo python3 -c "
from pathlib import Path
target = int('${TARGET_REPLICAS}')
p = Path('${UPSTREAM_CONF}')
s = p.read_text(encoding='utf-8')
lines = []
for i in range(1, target + 1):
    port = 3000 + (i - 1)
    lines.append(f'    server 127.0.0.1:{port} max_fails=3 fail_timeout=10s;')
block = '\\n'.join(lines)
import re
s2 = re.sub(r'(?ms)^upstream\\s+toolbox_backend\\s*\\{.*?\\n\\}', 'upstream toolbox_backend {\\n    least_conn;\\n    keepalive 64;\\n\\n' + block + '\\n}', s)
if s2 == s:
    raise SystemExit('Failed to rewrite upstream block in toolbox-upstream.conf')
p.write_text(s2, encoding='utf-8')
"
  sudo nginx -t
  sudo systemctl reload nginx
fi

echo
echo "Scale completed."
