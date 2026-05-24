#!/usr/bin/env bash
# One-shot: read DATABASE_URL from existing split env, redeploy with HOST_VERSION from $1
set -euo pipefail
HOST_VERSION="${1:?usage: ecs-run-deploy-split-remote.sh <host-version>}"
RUNTIME="/srv/apps/tool-box-split/.env.runtime"
line="$(grep -m1 '^DATABASE_URL=' "$RUNTIME")"
DB="${line#DATABASE_URL=}"
# strip optional surrounding quotes
DB="${DB%\"}"
DB="${DB#\"}"
export SKIP_DOCKER_LOGIN=1
export TOOLBOX_SPLIT_TOOLS="service-id-registry,mos-integration-toolbox,rsa-token-livestream,data-secure-manage"
export HOST_CHANGELOG="Toolbox split deploy ${HOST_VERSION}"
chmod +x /tmp/ecs-deploy-split.sh
exec /tmp/ecs-deploy-split.sh "$HOST_VERSION" "$DB" "47.116.180.173" 3000
