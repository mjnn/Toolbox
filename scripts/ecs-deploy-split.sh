#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <host-version> <database-url> <external-public-ip> [host-port] [sid-version] [mos-version] [rsa-version] [spec-revision]"
  echo "Env (recommended):"
  echo "  TOOLBOX_SPLIT_TOOLS=service-id-registry,mos-integration-toolbox,rsa-token-livestream,data-secure-manage"
  echo "  TOOLBOX_SPLIT_TOOL_<TOOL_KEY_UPPER>_VERSION=<version>   # optional per-tool version"
  exit 1
fi

HOST_VERSION="$1"
DATABASE_URL="$2"
EXTERNAL_PUBLIC_IP="$3"
HOST_PORT="${4:-3000}"
SID_VERSION="${5:-$HOST_VERSION}"
MOS_VERSION="${6:-$HOST_VERSION}"
RSA_VERSION="${7:-$HOST_VERSION}"
SPEC_REVISION="${8:-}"

REGISTRY="crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com"
HOST_IMAGE="$REGISTRY/mirror_ns/tool_box_host:${HOST_VERSION}"
TOOLS_REPO="$REGISTRY/mirror_ns/tool_box_tools"
REGISTRY_USERNAME="MjnnAliCloud"
SERVICE_NAME="tool-box-split"
BASE_DIR="${TOOLBOX_ECS_BASE_DIR:-/srv/apps}"
SERVICE_DIR="${BASE_DIR}/${SERVICE_NAME}"
RUNTIME_ENV_FILE="${SERVICE_DIR}/.env.runtime"
COMPOSE_FILE="${SERVICE_DIR}/compose.yaml"
HOST_CHANGELOG="${HOST_CHANGELOG:-Host 镜像 ${HOST_IMAGE} 部署发布}"
HOST_CHANGELOG_ESCAPED="${HOST_CHANGELOG//\"/\\\"}"

DEFAULT_TOOLS="service-id-registry,mos-integration-toolbox,rsa-token-livestream"
TOOL_LIST_RAW="${TOOLBOX_SPLIT_TOOLS:-$DEFAULT_TOOLS}"
IFS=',' read -r -a TOOL_KEYS <<< "$TOOL_LIST_RAW"
if [[ ${#TOOL_KEYS[@]} -eq 0 ]]; then
  echo "TOOLBOX_SPLIT_TOOLS is empty"
  exit 1
fi

sanitize_for_env() {
  local v="$1"
  v="${v//-/_}"
  v="${v//./_}"
  printf '%s' "${v^^}"
}

sanitize_for_service() {
  local v="$1"
  v="${v//_/-}"
  v="${v//./-}"
  printf '%s' "$v"
}

echo "Service: ${SERVICE_NAME}"
echo "Service directory: ${SERVICE_DIR}"

# Compose 选择：优先 Docker Compose v2（插件或 /usr/local/bin 独立包），避免 Ubuntu 自带
# python docker-compose 1.29.x 在重建容器时对新镜像元数据触发 KeyError: 'ContainerConfig'。
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
HOST_IMAGE=${HOST_IMAGE}
HOST_PORT=${HOST_PORT}
DATABASE_URL=${DATABASE_URL}
EXTERNAL_PUBLIC_IP=${EXTERNAL_PUBLIC_IP}
BACKEND_CORS_ORIGINS=["http://${EXTERNAL_PUBLIC_IP}","https://${EXTERNAL_PUBLIC_IP}","http://localhost","http://127.0.0.1"]
HOST_TOOLBOX_VERSION="${HOST_VERSION}"
HOST_TOOLBOX_SPEC_REVISION="${SPEC_REVISION}"
HOST_TOOLBOX_CHANGELOG="${HOST_CHANGELOG_ESCAPED}"
TOOLBOX_SPLIT_TOOLS=${TOOL_LIST_RAW}
EOF

UPSTREAMS=()
DEPENDS=()
TOOL_SERVICE_BLOCKS=()
TOOL_IMAGES=()
TOOL_CHANGELOG_ECHO=()

for tk in "${TOOL_KEYS[@]}"; do
  tool_key="$(echo "$tk" | xargs)"
  if [[ -z "$tool_key" ]]; then
    continue
  fi

  env_key="$(sanitize_for_env "$tool_key")"
  service_suffix="$(sanitize_for_service "$tool_key")"
  service_name="toolbox-tool-${service_suffix}"
  image_var="${env_key}_IMAGE"
  version_var="${env_key}_TOOLBOX_VERSION"
  spec_var="${env_key}_TOOLBOX_SPEC_REVISION"
  changelog_var="${env_key}_TOOLBOX_CHANGELOG"

  # Backward-compatible positional versions for default 3 tools.
  case "$tool_key" in
    service-id-registry) default_tool_ver="$SID_VERSION" ;;
    mos-integration-toolbox) default_tool_ver="$MOS_VERSION" ;;
    rsa-token-livestream) default_tool_ver="$RSA_VERSION" ;;
    *) default_tool_ver="$HOST_VERSION" ;;
  esac

  override_ver_var="TOOLBOX_SPLIT_TOOL_${env_key}_VERSION"
  tool_version="${!override_ver_var:-$default_tool_ver}"
  tool_image="${TOOLS_REPO}:${tool_key}-${tool_version}"
  changelog_override_var="${env_key}_CHANGELOG"
  tool_changelog="${!changelog_override_var:-${tool_key} 镜像 ${tool_image} 部署发布}"
  tool_changelog_escaped="${tool_changelog//\"/\\\"}"

  cat >>"${RUNTIME_ENV_FILE}" <<EOF
${image_var}=${tool_image}
${version_var}="${tool_version}"
${spec_var}="${SPEC_REVISION}"
${changelog_var}="${tool_changelog_escaped}"
EOF

  UPSTREAMS+=("${tool_key}=http://${service_name}:3000")
  DEPENDS+=("${service_name}")
  TOOL_IMAGES+=("${tool_image}")
  TOOL_CHANGELOG_ECHO+=("${tool_key}: ${tool_changelog}")

  TOOL_SERVICE_BLOCKS+=("
  ${service_name}:
    container_name: ${service_name}
    image: \${${image_var}}
    restart: unless-stopped
    environment:
      DATABASE_URL: \${DATABASE_URL}
      TOOLBOX_WORKERS: \"2\"
      TOOLBOX_LOAD_TOOL_PLUGINS: \"${tool_key}\"
      TOOLBOX_VISIBLE_TOOL_KEYS: \"${tool_key}\"
      SQLALCHEMY_POOL_SIZE: \"8\"
      SQLALCHEMY_MAX_OVERFLOW: \"4\"
      SQLALCHEMY_POOL_TIMEOUT: \"45\"
      SQLALCHEMY_POOL_RECYCLE: \"1800\"
      SQLALCHEMY_STATEMENT_TIMEOUT_MS: \"15000\"
      BACKEND_CORS_ORIGINS: \${BACKEND_CORS_ORIGINS}
      TOOLBOX_VERSION: \${${version_var}}
      TOOLBOX_SPEC_REVISION: \${${spec_var}}
      TOOLBOX_VERSION_TITLE: \"版本更新\"
      TOOLBOX_CHANGELOG: \${${changelog_var}}")
done

if [[ ${#UPSTREAMS[@]} -eq 0 ]]; then
  echo "No valid tool keys resolved from TOOLBOX_SPLIT_TOOLS=${TOOL_LIST_RAW}"
  exit 1
fi

UPSTREAMS_JOINED="$(IFS=','; echo "${UPSTREAMS[*]}")"

cat >"${COMPOSE_FILE}" <<EOF
services:
  toolbox-host:
    container_name: toolbox-host
    image: \${HOST_IMAGE}
    restart: unless-stopped
    ports:
      - "\${HOST_PORT}:3000"
    environment:
      DATABASE_URL: \${DATABASE_URL}
      TOOLBOX_EXTERNAL_PUBLIC_IP: \${EXTERNAL_PUBLIC_IP}
      TOOLBOX_WORKERS: "2"
      SQLALCHEMY_POOL_SIZE: "12"
      SQLALCHEMY_MAX_OVERFLOW: "8"
      SQLALCHEMY_POOL_TIMEOUT: "45"
      SQLALCHEMY_POOL_RECYCLE: "1800"
      SQLALCHEMY_STATEMENT_TIMEOUT_MS: "15000"
      BACKEND_CORS_ORIGINS: \${BACKEND_CORS_ORIGINS}
      TOOLBOX_LOAD_TOOL_PLUGINS: "none"
      TOOLBOX_TOOL_UPSTREAMS: "${UPSTREAMS_JOINED}"
      TOOLBOX_VERSION: \${HOST_TOOLBOX_VERSION}
      TOOLBOX_SPEC_REVISION: \${HOST_TOOLBOX_SPEC_REVISION}
      TOOLBOX_VERSION_TITLE: "版本更新"
      TOOLBOX_CHANGELOG: \${HOST_TOOLBOX_CHANGELOG}
    depends_on:
EOF

for dep in "${DEPENDS[@]}"; do
  echo "      - ${dep}" >> "${COMPOSE_FILE}"
done

cat >>"${COMPOSE_FILE}" <<'EOF'
    healthcheck:
      test:
        - CMD-SHELL
        - python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=5).read()"
      interval: 30s
      timeout: 6s
      retries: 3
      start_period: 20s
EOF

for block in "${TOOL_SERVICE_BLOCKS[@]}"; do
  printf "%b\n" "$block" >> "${COMPOSE_FILE}"
done

echo "Login registry: ${REGISTRY}"
if [[ "${SKIP_DOCKER_LOGIN:-}" == "1" ]]; then
  echo "SKIP_DOCKER_LOGIN=1: skipping docker login"
elif [[ -n "${REGISTRY_PASSWORD:-}" ]]; then
  printf '%s\n' "${REGISTRY_PASSWORD}" | docker login --username="${REGISTRY_USERNAME}" --password-stdin "${REGISTRY}"
else
  docker login --username="${REGISTRY_USERNAME}" "${REGISTRY}"
fi

echo "Pull images"
docker pull "${HOST_IMAGE}"
for img in "${TOOL_IMAGES[@]}"; do
  docker pull "$img"
done

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

echo "Tool list: ${TOOL_LIST_RAW}"
echo "Host health:"
curl -fsS "http://127.0.0.1:${HOST_PORT}/health" || true

