#!/usr/bin/env bash
set -euo pipefail

SPLIT_SERVICE="${1:-tool-box-split}"
LEGACY_SERVICE="${2:-tool-box-public}"
BASE_DIR="${TOOLBOX_ECS_BASE_DIR:-/srv/apps}"

split_dir="${BASE_DIR}/${SPLIT_SERVICE}"
legacy_dir="${BASE_DIR}/${LEGACY_SERVICE}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

if [[ -f "${split_dir}/compose.yaml" && -f "${split_dir}/.env.runtime" ]]; then
  echo "Stopping split stack: ${SPLIT_SERVICE}"
  ${COMPOSE_CMD} -p "${SPLIT_SERVICE}" --env-file "${split_dir}/.env.runtime" -f "${split_dir}/compose.yaml" down || true
fi

if [[ ! -f "${legacy_dir}/compose.yaml" || ! -f "${legacy_dir}/.env.runtime" ]]; then
  echo "Legacy stack files not found under ${legacy_dir}"
  exit 1
fi

echo "Starting legacy stack: ${LEGACY_SERVICE}"
${COMPOSE_CMD} -p "${LEGACY_SERVICE}" --env-file "${legacy_dir}/.env.runtime" -f "${legacy_dir}/compose.yaml" up -d

echo "Rollback complete. Current legacy status:"
${COMPOSE_CMD} -p "${LEGACY_SERVICE}" --env-file "${legacy_dir}/.env.runtime" -f "${legacy_dir}/compose.yaml" ps

