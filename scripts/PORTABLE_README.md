# Toolbox Portable Package

## Requirements

- Windows x64
- No Python / Node.js installation required

## One-click Startup

1. Double-click `start.cmd`
2. Wait for startup message
3. Browser opens local address and prints LAN address list
4. Other LAN devices can access `http://<your-lan-ip>:3000`

## One-click Stop

- Double-click `stop.cmd`

## Accounts and Database

- Portable startup does **not** auto-create demo accounts (`admin/owner/user`).
- Deploy mode is expected to connect to your production PostgreSQL (RDS).
- Copy `.env.example` to `.env` in the package root and fill production values (at least `DATABASE_URL`, `SECRET_KEY`, `BACKEND_CORS_ORIGINS`).

## Logs

- Backend runtime stdout: `logs/backend-runtime.out.log`
- Backend runtime stderr: `logs/backend-runtime.err.log`
- Backend API access: `logs/backend-access.log`
- Frontend access: `logs/frontend-access.log`
- App mixed log: `logs/app.log`

## Built-in performance acceptance scripts

This package now includes k6-based acceptance scripts:

- `scripts/run-perf-k6.ps1`: run one profile (`baseline` / `stress` / `custom`)
- `scripts/run-perf-suite.ps1`: run `baseline + stress + report`
- `scripts/report-perf-k6.ps1`: summarize one or more k6 JSON files
- Scenario file: `perf/k6-api.js`
- Output folder: `perf/results`

Quick example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-perf-suite.ps1 -BaseUrl "http://127.0.0.1:3000" -Token "<access_token>" -Label "deploy" -Quick
```

If k6 is not in PATH, install k6 on the deployment machine first.

## LAN Access Note

- Service binds `0.0.0.0:3000` by default.
- If LAN clients cannot connect, allow inbound TCP 3000 in Windows Firewall.

## Runtime concurrency (Uvicorn workers)

This is **not** related to whether `build-release.ps1` used parallel npm/pip on the build machine.

- **`TOOLBOX_WORKERS`**: number of backend processes when running from **source** (default **2** if unset). The **frozen `toolbox-backend.exe` always uses 1 worker** (PyInstaller + multiprocessing limitation).
- **`SQLALCHEMY_POOL_SIZE` / `SQLALCHEMY_MAX_OVERFLOW`**: per-process DB pool (PostgreSQL only). Defaults: `4` and `2`.

**Configuration**:

- `scripts/build-release.ps1` now copies `backend/.env.example` into the package as `.env.example`.
- By default it **does not** copy `backend/.env` (to avoid leaking local/prod secrets).
- If you really need to include it, build with `-IncludeBackendEnv`.
