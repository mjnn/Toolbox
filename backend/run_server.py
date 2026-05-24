import multiprocessing
import os
from pathlib import Path

import uvicorn


def _load_dotenv_if_present() -> None:
    """与 app.core.config_simple 一致的 .env 查找顺序（主进程在 import 配置前可先加载）。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    import sys

    def _exe_root() -> Path | None:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return None

    here = Path(__file__).resolve().parent
    candidates: list[Path] = []
    explicit = (os.getenv("TOOLBOX_BACKEND_ENV_FILE") or "").strip()
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path.cwd() / ".env")
    er = _exe_root()
    if er is not None:
        candidates.append(er / ".env")
    candidates.append(here / ".env")

    for p in candidates:
        if p.is_file():
            load_dotenv(p, override=False)
            break


def _resolve_workers() -> int:
    """
    Uvicorn 进程数（与「打包脚本是否并行」无关）。

    - 源码 / 直接 `python -m uvicorn`：未设置 TOOLBOX_WORKERS 时默认 2。
    - PyInstaller 冻结 exe：同样允许通过 TOOLBOX_WORKERS 控制，默认 2。
    """
    _load_dotenv_if_present()
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
