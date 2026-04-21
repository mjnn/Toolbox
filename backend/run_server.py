import multiprocessing
import os
from pathlib import Path

import uvicorn


def _load_dotenv_if_present() -> None:
    """便携包运行时 cwd 常为发布根目录，优先从 cwd 读 .env。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve().parent
    for p in (Path.cwd() / ".env", here / ".env", here.parent / ".env"):
        if p.is_file():
            load_dotenv(p)
            break


def _is_sqlite_url(url: str) -> bool:
    return url.strip().lower().startswith("sqlite")


def _resolve_workers() -> int:
    """
    Uvicorn 进程数（与「打包脚本是否并行」无关）。

    默认：PostgreSQL → 2；SQLite 文件 → 1（多进程共写同一 SQLite 文件不可靠）。
    规划依据见 docs/PORTABLE_PACKAGING_AGENT_RUNBOOK.md「运行时 Uvicorn worker」。
    """
    _load_dotenv_if_present()
    url = os.getenv("DATABASE_URL", "").strip()

    if not url or _is_sqlite_url(url):
        max_w = 1
    else:
        max_w = 8

    raw = os.getenv("TOOLBOX_WORKERS", "").strip()
    if raw:
        try:
            w = int(raw)
        except ValueError:
            w = 1
    else:
        w = 2 if max_w > 1 else 1

    w = max(1, min(w, max_w))
    return w


if __name__ == "__main__":
    # Required on Windows when using multiple processes (PyInstaller / spawn).
    multiprocessing.freeze_support()

    host = os.getenv("TOOLBOX_HOST", "0.0.0.0")
    port = int(os.getenv("TOOLBOX_PORT", "3000"))
    workers = _resolve_workers()

    # Multi-worker requires an import string so each process can load `main:app`.
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        workers=workers,
    )
