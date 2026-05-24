#!/usr/bin/env bash
# 在 ECS / 任意 Linux x86_64 上安装 Docker Compose v2 独立二进制到 /usr/local/bin/docker-compose，
# 供 PATH 优先于 /usr/bin/docker-compose（Ubuntu docker.io 附带的 python 版 1.29）使用。
# 部署脚本 ecs-deploy-split.sh / ecs-deploy-public.sh 会优先探测该路径下的 v2。
set -euo pipefail

COMPOSE_VERSION="${COMPOSE_VERSION:-2.32.4}"
URL="https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-linux-x86_64"
TARGET="/usr/local/bin/docker-compose"
# 官方 release 约 62MiB；明显偏小视为下载损坏
MIN_BYTES="${MIN_BYTES:-60000000}"
TMP="$(mktemp)"

cleanup() { rm -f "${TMP}"; }
trap cleanup EXIT

echo "Downloading Docker Compose v${COMPOSE_VERSION} ..."
if command -v curl >/dev/null 2>&1; then
  curl -fSL --retry 8 --retry-delay 3 --connect-timeout 20 --max-time 1800 "${URL}" -o "${TMP}"
else
  wget -q --show-progress -O "${TMP}" "${URL}"
fi

sz="$(wc -c <"${TMP}" | tr -d ' ')"
if [[ "${sz}" -lt "${MIN_BYTES}" ]]; then
  echo "Download too small (${sz} bytes), expected at least ${MIN_BYTES}. Remove partial file and retry on a stable network."
  exit 1
fi

if ! file "${TMP}" | grep -q 'ELF 64-bit'; then
  echo "Download is not a Linux x86_64 ELF binary."
  exit 1
fi

install -m 0755 "${TMP}" "${TARGET}"
echo "Installed: ${TARGET}"
"${TARGET}" version
