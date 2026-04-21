import base64
import hashlib
import json

from legacy_paths import static_path


def _decrypt_password(encrypted_value: str) -> str:
    try:
        from cryptography.fernet import Fernet  # optional dependency in old runtime
        try:
            from app.core.config_simple import SECRET_KEY  # backend runtime
        except Exception:
            SECRET_KEY = "your-strong-secret-key-change-in-production"
        key_material = hashlib.sha256(SECRET_KEY.encode("utf-8")).digest()
        fernet_key = base64.urlsafe_b64encode(key_material)
        return Fernet(fernet_key).decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def get_account_password(section: str) -> tuple[str, str]:
    config_file = static_path("config", "account&password.json")
    data = json.loads(config_file.read_text(encoding="utf-8"))
    section_data = data.get(section, {}) if isinstance(data, dict) else {}
    username = str(section_data.get("account") or "")
    encrypted = str(section_data.get("password_enc") or "").strip()
    if encrypted:
        password = _decrypt_password(encrypted)
        if password:
            return username, password
    return username, str(section_data.get("password") or "")
