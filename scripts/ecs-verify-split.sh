#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${1:-tool-box-split}"
BASE_DIR="${TOOLBOX_ECS_BASE_DIR:-/srv/apps}"
SERVICE_DIR="${BASE_DIR}/${SERVICE_NAME}"
RUNTIME_ENV_FILE="${SERVICE_DIR}/.env.runtime"
COMPOSE_FILE="${SERVICE_DIR}/compose.yaml"

if [[ ! -f "${RUNTIME_ENV_FILE}" || ! -f "${COMPOSE_FILE}" ]]; then
  echo "Missing ${RUNTIME_ENV_FILE} or ${COMPOSE_FILE}"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

source "${RUNTIME_ENV_FILE}"
HOST_PORT="${HOST_PORT:-3000}"

echo "== Compose status =="
${COMPOSE_CMD} -p "${SERVICE_NAME}" --env-file "${RUNTIME_ENV_FILE}" -f "${COMPOSE_FILE}" ps

echo "== Docker status =="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | \
  awk 'NR==1 || /toolbox-host|toolbox-tool-service-id|toolbox-tool-mos|toolbox-tool-rsa/'

echo "== Host health =="
curl -fsS "http://127.0.0.1:${HOST_PORT}/health"
echo

echo "== Tools list =="
curl -fsS "http://127.0.0.1:${HOST_PORT}/api/v1/tools/?skip=0&limit=20"
echo

echo "== Feature smoke (auth may return 401/403, but should not be 404 from host routing) =="
for path in \
  "/api/v1/tools/1/features/service-id-entries" \
  "/api/v1/tools/2/features/sim-query" \
  "/api/v1/tools/3/features/livestream/config"
do
  code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${HOST_PORT}${path}")"
  echo "${path} -> ${code}"
done

