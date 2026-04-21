import multiprocessing
import os
import sys
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


def _resolve_workers() -> int:
    """
    Uvicorn 进程数（与「打包脚本是否并行」无关）。

    - 源码 / 直接 `python -m uvicorn`：未设置 TOOLBOX_WORKERS 时默认 2（见 docs 规划）。
    - PyInstaller 冻结 exe：**固定 1**。多 worker 会 spawn 子进程，子进程无法按 `main:app` 正确导入打包后的模块，导致启动失败。
    """
    _load_dotenv_if_present()
    if getattr(sys, "frozen", False):
        return 1
    raw = os.getenv("TOOLBOX_WORKERS", "").strip()
    if raw:
        try:
            w = int(raw)
        except ValueError:
            w = 2
    else:
        w = 2
    return max(1, min(w, 8))


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
