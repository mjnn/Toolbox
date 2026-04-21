import multiprocessing
import os

import uvicorn

if __name__ == "__main__":
    # Required on Windows when using multiple processes (PyInstaller / spawn).
    multiprocessing.freeze_support()

    host = os.getenv("TOOLBOX_HOST", "0.0.0.0")
    port = int(os.getenv("TOOLBOX_PORT", "3000"))
    _raw_workers = os.getenv("TOOLBOX_WORKERS", "1").strip()
    try:
        workers = int(_raw_workers) if _raw_workers else 1
    except ValueError:
        workers = 1
    if workers < 1:
        workers = 1

    # Multi-worker requires an import string so each process can load `main:app`.
    # Single worker keeps the same behavior as before (one process).
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        workers=workers,
    )
