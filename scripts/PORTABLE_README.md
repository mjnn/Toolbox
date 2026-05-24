# Toolbox Portable Package

## Requirements

- Windows x64
- No Python / Node.js installation required

## One-click Startup (split only)

1. Double-click `start.cmd`（默认就是 split）
2. Wait for startup message
3. Browser opens local address and prints LAN address list
4. Other LAN devices can access `http://<your-lan-ip>:3000`

## One-click Stop

- Double-click `stop.cmd`

## Split mode process topology (default and only mode)

- Host: `0.0.0.0:3000` (single user entry)
- Tool runtime (internal only):
  - `127.0.0.1:3001` service-id-registry
  - `127.0.0.1:3002` mos-integration-toolbox
  - `127.0.0.1:3003` rsa-token-livestream
  - `127.0.0.1:3004` data-secure-manage

The host uses `TOOLBOX_TOOL_UPSTREAMS` to proxy `/api/v1/tools/{tool_id}/features/*` to tool runtimes, so frontend/API paths remain unchanged for users.
- Optional shortcut remains available: `start-split.cmd` / `stop-split.cmd`
- Restart one tool only: `restart-tool.cmd <host|service-id|mos|rsa|data-secure|all>`
- Advanced control: `tool-control.ps1 -Action <status|start|stop|restart> -Tool <all|host|service-id|mos|rsa|data-secure>`

## Notes

便携包已统一为 split 运行模式，不再提供单进程启动入口。

## Accounts and Database

- Portable startup does **not** auto-create demo accounts (`admin/owner/user`).
- Deploy mode is expected to connect to your production PostgreSQL (RDS).
- **Configuration file**: at runtime the backend loads the first existing file among `TOOLBOX_BACKEND_ENV_FILE` (if set), current working directory `.env`, or `.env` next to `toolbox-backend.exe`. When you run `scripts/build-release.ps1` on a machine that already has `backend/.env`, that file is **copied to the package root as `.env`** automatically. Otherwise copy `backend/.env.example` to `.env` in the package root and fill values (`DATABASE_URL`, `SECRET_KEY`, `BACKEND_CORS_ORIGINS`, etc.).  
  精简包（`-MinimalIntranetPackage`）不含 `.env.example`，需自备 `.env`。

## Logs

- Backend runtime stdout: `logs/backend-runtime.out.log`
- Backend runtime stderr: `logs/backend-runtime.err.log`
- Backend API access: `logs/backend-access.log`
- Frontend access: `logs/frontend-access.log`
- App mixed log: `logs/app.log`

## Performance acceptance scripts (optional)

When not built with `-MinimalIntranetPackage`, the package includes k6-based scripts under `scripts/` and `perf/`.

- `scripts/run-perf-k6.ps1`: uses `k6` on **PATH**, or `ops\k6.exe` if you create an `ops` folder and drop `k6.exe` there
- `scripts/run-perf-suite.ps1`, `scripts/report-perf-k6.ps1`, scenario `perf/k6-api.js`, output `perf/results`

Quick example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-suite.ps1 -BaseUrl "http://127.0.0.1:3000" -Token "<access_token>" -Label "deploy" -Quick
```

## LAN Access Note

- Single-process mode binds `0.0.0.0:3000` by default.
- If LAN clients cannot connect, allow inbound TCP 3000 in Windows Firewall.

## Runtime concurrency (Uvicorn workers)

This is **not** related to whether `scripts/build-release.ps1` used parallel npm/pip on the build machine.

- **`TOOLBOX_WORKERS`**: number of backend processes for both source and portable executable (default **2** if unset).
- **`SQLALCHEMY_POOL_SIZE` / `SQLALCHEMY_MAX_OVERFLOW`**: per-process DB pool (PostgreSQL only). Recommended defaults: `12` / `8`.
- **`SQLALCHEMY_POOL_TIMEOUT` / `SQLALCHEMY_POOL_RECYCLE` / `SQLALCHEMY_STATEMENT_TIMEOUT_MS`**: recommended defaults `45` / `1800` / `15000`.

**Configuration**

- `scripts/build-release.ps1` copies `backend/.env.example` into the package as `.env.example` (unless `-MinimalIntranetPackage`).
- By default it **does not** copy `backend/.env` (to avoid leaking local/prod secrets).
- If you really need to include it, build with `-IncludeBackendEnv`.
