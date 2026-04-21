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
