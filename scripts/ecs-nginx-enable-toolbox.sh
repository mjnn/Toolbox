#!/usr/bin/env bash
set -euo pipefail

NGINX_UPSTREAM_CONF="/etc/nginx/conf.d/toolbox-upstream.conf"
NGINX_SNIPPET_CONF="/etc/nginx/snippets/toolbox-locations.conf"
NGINX_SITE_DEFAULT="/etc/nginx/sites-enabled/default"
INCLUDE_LINE="    include /etc/nginx/snippets/toolbox-locations.conf;"

echo "Writing ${NGINX_UPSTREAM_CONF}"
sudo tee "${NGINX_UPSTREAM_CONF}" >/dev/null <<'EOF'
upstream toolbox_backend {
    least_conn;
    keepalive 64;

    server 127.0.0.1:3000 max_fails=3 fail_timeout=10s;
    # server 127.0.0.1:3001 max_fails=3 fail_timeout=10s;
}

map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
EOF

echo "Writing ${NGINX_SNIPPET_CONF}"
sudo tee "${NGINX_SNIPPET_CONF}" >/dev/null <<'EOF'
location /toolbox/ {
    proxy_pass http://toolbox_backend/;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_connect_timeout 5s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

location /api/v1/ {
    proxy_pass http://toolbox_backend/api/v1/;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_connect_timeout 5s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

location = /health {
    proxy_pass http://toolbox_backend/health;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 3s;
    proxy_send_timeout 10s;
    proxy_read_timeout 10s;
}
EOF

echo "Ensuring include in ${NGINX_SITE_DEFAULT}"
sudo python3 -c "
from pathlib import Path
p = Path('${NGINX_SITE_DEFAULT}')
s = p.read_text(encoding='utf-8')
include_line = '${INCLUDE_LINE}'
if include_line not in s:
    needle = '    location / {'
    if needle not in s:
        raise SystemExit('Cannot find insertion point in nginx default site config')
    s = s.replace(needle, include_line + '\\n\\n' + needle, 1)
    p.write_text(s, encoding='utf-8')
"

echo "Testing nginx config"
sudo nginx -t

echo "Reloading nginx"
sudo systemctl reload nginx

echo "Nginx toolbox proxy enabled"
echo "Test URLs:"
echo "  http://<ecs-ip>/toolbox/"
echo "  http://<ecs-ip>/api/v1/tools/?skip=0&limit=10"
