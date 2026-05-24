#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <image-version> <database-url> [host-port] [external-public-ip] [toolbox-version] [spec-revision] [changelog]"
  exit 1
fi

VERSION="$1"
DATABASE_URL="$2"
HOST_PORT="${3:-3000}"
EXTERNAL_PUBLIC_IP="${4:-47.116.180.173}"
TOOLBOX_VERSION="${5:-$VERSION}"
TOOLBOX_SPEC_REVISION="${6:-}"
TOOLBOX_CHANGELOG="${7:-镜像 ${IMAGE} 部署发布}"
TOOLBOX_CHANGELOG_ESCAPED="${TOOLBOX_CHANGELOG//\"/\\\"}"

REGISTRY="crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com"
IMAGE="$REGISTRY/mirror_ns/tool_box:${VERSION}"
REGISTRY_USERNAME="MjnnAliCloud"
SERVICE_NAME="tool-box-public"
BASE_DIR="${TOOLBOX_ECS_BASE_DIR:-/srv/apps}"
SERVICE_DIR="${BASE_DIR}/${SERVICE_NAME}"
RUNTIME_ENV_FILE="${SERVICE_DIR}/.env.runtime"
COMPOSE_FILE="${SERVICE_DIR}/compose.yaml"

echo "Service: ${SERVICE_NAME}"
echo "Image: ${IMAGE}"
echo "Service directory: ${SERVICE_DIR}"

pick_compose_cmd() {
  if [[ -n "${TOOLBOX_COMPOSE_CMD:-}" ]]; then
    printf '%s' "${TOOLBOX_COMPOSE_CMD}"
    return 0
  fi
  if docker compose version >/dev/null 2>&1; then
    printf 'docker compose'
    return 0
  fi
  if [[ -x /usr/local/bin/docker-compose ]]; then
    if /usr/local/bin/docker-compose version 2>/dev/null | grep -qiE '^Docker Compose version v2'; then
      printf '/usr/local/bin/docker-compose'
      return 0
    fi
  fi
  if docker-compose version >/dev/null 2>&1; then
    printf 'docker-compose'
    return 0
  fi
  return 1
}
if ! COMPOSE_CMD="$(pick_compose_cmd)"; then
  echo "未找到 docker compose / docker-compose。可在 ECS 执行: bash scripts/ecs-install-compose-v2-bin.sh"
  exit 1
fi
echo "Using compose command: ${COMPOSE_CMD}"

mkdir -p "${SERVICE_DIR}"

cat >"${RUNTIME_ENV_FILE}" <<EOF
SERVICE_NAME=${SERVICE_NAME}
IMAGE=${IMAGE}
HOST_PORT=${HOST_PORT}
DATABASE_URL=${DATABASE_URL}
EXTERNAL_PUBLIC_IP=${EXTERNAL_PUBLIC_IP}
BACKEND_CORS_ORIGINS=["http://${EXTERNAL_PUBLIC_IP}","https://${EXTERNAL_PUBLIC_IP}","http://localhost","http://127.0.0.1"]
TOOLBOX_VERSION="${TOOLBOX_VERSION}"
TOOLBOX_SPEC_REVISION="${TOOLBOX_SPEC_REVISION}"
TOOLBOX_CHANGELOG="${TOOLBOX_CHANGELOG_ESCAPED}"
EOF

cat >"${COMPOSE_FILE}" <<'EOF'
services:
  toolbox-public:
    container_name: ${SERVICE_NAME}
    image: ${IMAGE}
    restart: unless-stopped
    ports:
      - "${HOST_PORT}:3000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      TOOLBOX_EXTERNAL_PUBLIC_IP: ${EXTERNAL_PUBLIC_IP}
      TOOLBOX_VISIBLE_TOOL_KEYS: service-id-registry
      TOOLBOX_WORKERS: "2"
      SQLALCHEMY_POOL_SIZE: "12"
      SQLALCHEMY_MAX_OVERFLOW: "8"
      SQLALCHEMY_POOL_TIMEOUT: "45"
      SQLALCHEMY_POOL_RECYCLE: "1800"
      SQLALCHEMY_STATEMENT_TIMEOUT_MS: "15000"
      BACKEND_CORS_ORIGINS: ${BACKEND_CORS_ORIGINS}
      TOOLBOX_VERSION: ${TOOLBOX_VERSION}
      TOOLBOX_SPEC_REVISION: ${TOOLBOX_SPEC_REVISION}
      TOOLBOX_VERSION_TITLE: "版本更新"
      TOOLBOX_CHANGELOG: ${TOOLBOX_CHANGELOG}
      # 可选：仅加载部分工具插件（Tool.name，逗号分隔），与全量默认行为见 docs/ECS_TOOL_RUNTIME_TOPOLOGY.md
      # TOOLBOX_LOAD_TOOL_PLUGINS: "service-id-registry"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
    healthcheck:
      test:
        - CMD-SHELL
        - python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=5).read()"
      interval: 30s
      timeout: 6s
      retries: 3
      start_period: 20s
EOF

if docker ps -a --format '{{.Names}}' | grep -Eq "^${SERVICE_NAME}$"; then
  echo "Removing existing standalone container: ${SERVICE_NAME}"
  docker rm -f "${SERVICE_NAME}"
fi

if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${HOST_PORT}$"; then
  echo "Port ${HOST_PORT} is already in use."
  exit 1
fi

echo "Login registry: ${REGISTRY}"
if [[ "${SKIP_DOCKER_LOGIN:-}" == "1" ]]; then
  echo "SKIP_DOCKER_LOGIN=1: skipping docker login (use when host已配置 registry 凭据，或非交互 SSH)。"
elif [[ -n "${REGISTRY_PASSWORD:-}" ]]; then
  printf '%s\n' "${REGISTRY_PASSWORD}" | docker login --username="${REGISTRY_USERNAME}" --password-stdin "${REGISTRY}"
else
  docker login --username="${REGISTRY_USERNAME}" "${REGISTRY}"
fi

echo "Pull image: ${IMAGE}"
docker pull "${IMAGE}"

echo "Deploying with docker compose"
if [[ "${COMPOSE_CMD}" == "docker compose" ]]; then
  ${COMPOSE_CMD} \
    --project-name "${SERVICE_NAME}" \
    --env-file "${RUNTIME_ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    up -d --remove-orphans
else
  ${COMPOSE_CMD} \
    -p "${SERVICE_NAME}" \
    --env-file "${RUNTIME_ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    up -d --remove-orphans
fi

echo "Container status:"
if [[ "${COMPOSE_CMD}" == "docker compose" ]]; then
  ${COMPOSE_CMD} \
    --project-name "${SERVICE_NAME}" \
    --env-file "${RUNTIME_ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    ps
else
  ${COMPOSE_CMD} \
    -p "${SERVICE_NAME}" \
    --env-file "${RUNTIME_ENV_FILE}" \
    -f "${COMPOSE_FILE}" \
    ps
fi

echo "Health check:"
sleep 2
curl --max-time 8 -sS "http://127.0.0.1:${HOST_PORT}/health" || true

echo "Service files:"
echo "  ${RUNTIME_ENV_FILE}"
echo "  ${COMPOSE_FILE}"

