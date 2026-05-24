#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/srv/apps"
mkdir -p "${BASE_DIR}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif docker-compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "docker compose/docker-compose is required but not available"
  exit 1
fi

write_service_files() {
  local service_dir="$1"
  local env_content="$2"
  local compose_content="$3"

  mkdir -p "${service_dir}"
  printf "%s\n" "${env_content}" > "${service_dir}/.env.runtime"
  printf "%s\n" "${compose_content}" > "${service_dir}/compose.yaml"
}

SIM_ENV_CONTENT='SERVICE_NAME=sim_api
IMAGE=crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/sim-api:v2.4
HOST_PORT=5000
CONTAINER_PORT=5000'

SIM_COMPOSE_CONTENT='services:
  sim_api:
    container_name: ${SERVICE_NAME}
    image: ${IMAGE}
    restart: unless-stopped
    ports:
      - "${HOST_PORT}:${CONTAINER_PORT}"
    volumes:
      - "/home/admin/sim_config/config:/GetSIMInfoAPI/config"
    command:
      - "gunicorn"
      - "--bind"
      - "0.0.0.0:5000"
      - "--workers"
      - "4"
      - "--threads"
      - "2"
      - "app:app"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"'

FILE_SERVER_ENV_CONTENT='SERVICE_NAME=file_server
IMAGE=crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/file_server:v1.0
HOST_PORT=8888
CONTAINER_PORT=8888'

FILE_SERVER_COMPOSE_CONTENT='services:
  file_server:
    container_name: ${SERVICE_NAME}
    image: ${IMAGE}
    restart: always
    ports:
      - "${HOST_PORT}:${CONTAINER_PORT}"
    volumes:
      - "/home/admin/files:/app/files"
    command:
      - "uvicorn"
      - "main:app"
      - "--host"
      - "0.0.0.0"
      - "--port"
      - "8888"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"'

FUND_ENV_CONTENT='SERVICE_NAME=fund_value_em
IMAGE=crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com/mirror_ns/fund_value_em:v1.0
HOST_PORT=8001
CONTAINER_PORT=8000'

FUND_COMPOSE_CONTENT='services:
  fund_value_em:
    container_name: ${SERVICE_NAME}
    image: ${IMAGE}
    restart: always
    ports:
      - "${HOST_PORT}:${CONTAINER_PORT}"
    command:
      - "uvicorn"
      - "main:app"
      - "--host"
      - "0.0.0.0"
      - "--port"
      - "8000"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"'

write_service_files "${BASE_DIR}/sim_api" "${SIM_ENV_CONTENT}" "${SIM_COMPOSE_CONTENT}"
write_service_files "${BASE_DIR}/file_server" "${FILE_SERVER_ENV_CONTENT}" "${FILE_SERVER_COMPOSE_CONTENT}"
write_service_files "${BASE_DIR}/fund_value_em" "${FUND_ENV_CONTENT}" "${FUND_COMPOSE_CONTENT}"

echo "Created compose definitions under ${BASE_DIR}"

# Stop and remove legacy containers before compose-managed startup.
for legacy in sim_api admiring_joliot musing_feynman; do
  if docker ps -a --format '{{.Names}}' | awk '{print $1}' | awk -v n="$legacy" '$1==n{found=1} END{exit !found}'; then
    echo "Removing legacy container: ${legacy}"
    docker rm -f "${legacy}"
  fi
done

if [[ "${COMPOSE_CMD}" == "docker compose" ]]; then
  ${COMPOSE_CMD} --project-name sim_api --env-file "${BASE_DIR}/sim_api/.env.runtime" -f "${BASE_DIR}/sim_api/compose.yaml" up -d --remove-orphans
  ${COMPOSE_CMD} --project-name file_server --env-file "${BASE_DIR}/file_server/.env.runtime" -f "${BASE_DIR}/file_server/compose.yaml" up -d --remove-orphans
  ${COMPOSE_CMD} --project-name fund_value_em --env-file "${BASE_DIR}/fund_value_em/.env.runtime" -f "${BASE_DIR}/fund_value_em/compose.yaml" up -d --remove-orphans
else
  ${COMPOSE_CMD} -p sim_api --env-file "${BASE_DIR}/sim_api/.env.runtime" -f "${BASE_DIR}/sim_api/compose.yaml" up -d --remove-orphans
  ${COMPOSE_CMD} -p file_server --env-file "${BASE_DIR}/file_server/.env.runtime" -f "${BASE_DIR}/file_server/compose.yaml" up -d --remove-orphans
  ${COMPOSE_CMD} -p fund_value_em --env-file "${BASE_DIR}/fund_value_em/.env.runtime" -f "${BASE_DIR}/fund_value_em/compose.yaml" up -d --remove-orphans
fi

echo "Migration finished. Current services:"
docker ps | awk 'NR==1 || /sim_api|file_server|fund_value_em/'
