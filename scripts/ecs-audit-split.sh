#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${1:-tool-box-split}"
BASE_DIR="${TOOLBOX_ECS_BASE_DIR:-/srv/apps}"
SERVICE_DIR="${BASE_DIR}/${SERVICE_NAME}"
RUNTIME_ENV_FILE="${SERVICE_DIR}/.env.runtime"
COMPOSE_FILE="${SERVICE_DIR}/compose.yaml"

if [[ ! -f "${RUNTIME_ENV_FILE}" || ! -f "${COMPOSE_FILE}" ]]; then
  echo "Missing split runtime files:"
  echo "  - ${RUNTIME_ENV_FILE}"
  echo "  - ${COMPOSE_FILE}"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

source "${RUNTIME_ENV_FILE}"
HOST_PORT="${HOST_PORT:-3000}"

echo "=== Split Stack Summary ==="
echo "service: ${SERVICE_NAME}"
echo "dir    : ${SERVICE_DIR}"
echo "port   : ${HOST_PORT}"
echo

echo "=== Compose Status ==="
${COMPOSE_CMD} -p "${SERVICE_NAME}" --env-file "${RUNTIME_ENV_FILE}" -f "${COMPOSE_FILE}" ps
echo

echo "=== Host Health ==="
curl -fsS "http://127.0.0.1:${HOST_PORT}/health"
echo
echo

echo "=== Tool List API ==="
curl -fsS "http://127.0.0.1:${HOST_PORT}/api/v1/tools/?skip=0&limit=20"
echo
echo

echo "=== Feature Route Smoke (expected 401/403 if unauthenticated; must NOT be 404 due to host routing) ==="
declare -a checks=(
  "/api/v1/tools/1/features/service-id-entries"
  "/api/v1/tools/2/features/sim-query"
  "/api/v1/tools/4/features/livestream/config"
)
for p in "${checks[@]}"; do
  code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${HOST_PORT}${p}")"
  echo "${p} -> ${code}"
done
echo

echo "=== Snapshot Hint ==="
echo "cp ${COMPOSE_FILE} ${COMPOSE_FILE}.bak-\$(date +%Y%m%d-%H%M%S)"
echo "cp ${RUNTIME_ENV_FILE} ${RUNTIME_ENV_FILE}.bak-\$(date +%Y%m%d-%H%M%S)"
echo

echo "=== Rollback Hint ==="
echo "bash scripts/ecs-rollback-split.sh"
