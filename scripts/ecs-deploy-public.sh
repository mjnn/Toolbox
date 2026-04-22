#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <image-version> <database-url> [host-port] [external-public-ip]"
  exit 1
fi

VERSION="$1"
DATABASE_URL="$2"
HOST_PORT="${3:-3000}"
EXTERNAL_PUBLIC_IP="${4:-47.116.180.173}"

REGISTRY="crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com"
IMAGE="$REGISTRY/mirror_ns/tool_box:${VERSION}"
CONTAINER_NAME="tool-box-public"

echo "Login registry: $REGISTRY"
docker login --username=MjnnAliCloud "$REGISTRY"

if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}$"; then
  echo "Removing existing container: $CONTAINER_NAME"
  docker rm -f "$CONTAINER_NAME"
fi

if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${HOST_PORT}$"; then
  echo "Port $HOST_PORT is already in use."
  exit 1
fi

echo "Pull image: $IMAGE"
docker pull "$IMAGE"

echo "Starting container on port $HOST_PORT"
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p "${HOST_PORT}:3000" \
  -e "DATABASE_URL=$DATABASE_URL" \
  -e "TOOLBOX_EXTERNAL_PUBLIC_IP=$EXTERNAL_PUBLIC_IP" \
  -e 'TOOLBOX_VISIBLE_TOOL_KEYS=service-id-registry' \
  -e 'TOOLBOX_WORKERS=1' \
  -e 'BACKEND_CORS_ORIGINS=["http://47.116.180.173","https://47.116.180.173","http://localhost","http://127.0.0.1"]' \
  "$IMAGE"

echo "Container started:"
docker ps --filter "name=$CONTAINER_NAME"
echo "Health check:"
curl --max-time 8 -sS "http://127.0.0.1:${HOST_PORT}/health" || true

