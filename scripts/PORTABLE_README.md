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

## Default Accounts (auto-created at startup)

- Admin: `admin / admin123`
- Feature owner: `owner / owner123`
- Normal user: `user / user12345`

## Logs

- Backend runtime stdout: `logs/backend-runtime.out.log`
- Backend runtime stderr: `logs/backend-runtime.err.log`
- Backend API access: `logs/backend-access.log`
- Frontend access: `logs/frontend-access.log`
- App mixed log: `logs/app.log`

## LAN Access Note

- Service binds `0.0.0.0:3000` by default.
- If LAN clients cannot connect, allow inbound TCP 3000 in Windows Firewall.

## Runtime concurrency (Uvicorn workers)

This is **not** related to whether `build-release.ps1` used parallel npm/pip on the build machine.

- **`TOOLBOX_WORKERS`**: number of backend processes when running from **source** (default **2** if unset). The **frozen `toolbox-backend.exe` always uses 1 worker** (PyInstaller + multiprocessing limitation).
- **`SQLALCHEMY_POOL_SIZE` / `SQLALCHEMY_MAX_OVERFLOW`**: per-process DB pool (PostgreSQL only). Defaults: `4` and `2`.

Place a `.env` next to `toolbox-backend.exe` (package root) or set variables before `start.cmd`. See `docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md` §3.1 for sizing notes (e.g. ~10 concurrent users on 1 vCPU / 2GB PostgreSQL).
