import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _rotating_handler(path: Path, formatter: logging.Formatter) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


def setup_logging() -> None:
    configured = logging.getLogger("app.logging")
    if configured.handlers:
        return

    log_dir = Path(os.getenv("TOOLBOX_LOG_DIR", Path.cwd() / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(_rotating_handler(log_dir / "app.log", formatter))

    # API/Backend access log
    backend_access_logger = logging.getLogger("access.backend")
    backend_access_logger.setLevel(logging.INFO)
    backend_access_logger.propagate = False
    if not backend_access_logger.handlers:
        backend_access_logger.addHandler(
            _rotating_handler(log_dir / "backend-access.log", formatter)
        )

    # Frontend static/spa access log
    frontend_access_logger = logging.getLogger("access.frontend")
    frontend_access_logger.setLevel(logging.INFO)
    frontend_access_logger.propagate = False
    if not frontend_access_logger.handlers:
        frontend_access_logger.addHandler(
            _rotating_handler(log_dir / "frontend-access.log", formatter)
        )

    configured.addHandler(logging.NullHandler())
