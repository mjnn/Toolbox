#!/usr/bin/env bash
set -euo pipefail

echo "=== Host ==="
hostname
uname -a
echo

echo "=== Running Containers ==="
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
echo

echo "=== Exited/Created Containers (needs cleanup) ==="
docker ps -a --filter status=exited --filter status=created --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
echo

echo "=== Image Disk Usage ==="
docker system df
echo

echo "=== Listening TCP Ports ==="
ss -ltn
echo

echo "=== Suggested next commands (manual review first) ==="
echo "docker ps -a --filter status=exited --format '{{.ID}} {{.Names}}'"
echo "docker rm <container-id>"
echo "docker image prune -f"
