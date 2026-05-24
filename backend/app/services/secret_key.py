"""Read application secret key for crypto helpers (keeps service modules off direct config import spam)."""
from __future__ import annotations

import os


def get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "your-strong-secret-key-change-in-production")
