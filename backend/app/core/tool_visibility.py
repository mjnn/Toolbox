from __future__ import annotations

import contextvars
import json
import os
from pathlib import Path
from typing import Any

from app.core.config_simple import BACKEND_ROOT

RUNTIME_ENV_INTERNAL = "internal"
RUNTIME_ENV_EXTERNAL = "external"
_SUPPORTED_RUNTIME_ENVS = {RUNTIME_ENV_INTERNAL, RUNTIME_ENV_EXTERNAL}
_DEFAULT_EXTERNAL_HOST = os.getenv("TOOLBOX_EXTERNAL_PUBLIC_IP", "47.116.180.173").strip()
_CONFIG_FILE = Path(BACKEND_ROOT) / "runtime" / "tool_visibility.json"
_REQUEST_RUNTIME_ENV: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_runtime_env",
    default=None,
)


def _parse_visible_tool_keys(raw: str | None) -> list[str]:
    return sorted(
        {
            item.strip()
            for item in (raw or "").split(",")
            if item and item.strip()
        }
    )


def _normalize_host(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return ""
    if "," in value:
        value = value.split(",", 1)[0].strip()
    if value.startswith("[") and "]" in value:
        value = value[1 : value.index("]")]
    elif ":" in value:
        value = value.split(":", 1)[0].strip()
    return value


def _default_config() -> dict[str, Any]:
    external_hosts: list[str] = []
    if _DEFAULT_EXTERNAL_HOST:
        external_hosts.append(_DEFAULT_EXTERNAL_HOST)
    legacy_external_visible = _parse_visible_tool_keys(os.getenv("TOOLBOX_VISIBLE_TOOL_KEYS"))
    return {
        "external_hosts": external_hosts,
        "internal_visible_tool_keys": [],
        "external_visible_tool_keys": legacy_external_visible,
    }


def _normalize_config(raw: dict[str, Any]) -> dict[str, Any]:
    default = _default_config()
    external_hosts = raw.get("external_hosts", default["external_hosts"])
    internal_keys = raw.get("internal_visible_tool_keys", default["internal_visible_tool_keys"])
    external_keys = raw.get("external_visible_tool_keys", default["external_visible_tool_keys"])
    return {
        "external_hosts": sorted(
            {
                _normalize_host(v)
                for v in external_hosts
                if isinstance(v, str) and _normalize_host(v)
            }
        ),
        "internal_visible_tool_keys": sorted(
            {str(v).strip() for v in internal_keys if str(v).strip()}
        ),
        "external_visible_tool_keys": sorted(
            {str(v).strip() for v in external_keys if str(v).strip()}
        ),
    }


def load_tool_visibility_config() -> dict[str, Any]:
    if not _CONFIG_FILE.exists():
        return _default_config()
    try:
        raw = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _default_config()
    if not isinstance(raw, dict):
        return _default_config()
    return _normalize_config(raw)


def save_tool_visibility_config(
    *,
    external_hosts: list[str],
    internal_visible_tool_keys: list[str],
    external_visible_tool_keys: list[str],
) -> dict[str, Any]:
    payload = _normalize_config(
        {
            "external_hosts": external_hosts,
            "internal_visible_tool_keys": internal_visible_tool_keys,
            "external_visible_tool_keys": external_visible_tool_keys,
        }
    )
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def resolve_runtime_environment(host: str | None = None) -> tuple[str, str]:
    forced_env = (os.getenv("TOOLBOX_DEPLOY_ENV") or "").strip().lower()
    if forced_env in _SUPPORTED_RUNTIME_ENVS:
        return forced_env, "forced_env"

    cfg = load_tool_visibility_config()
    normalized_host = _normalize_host(host)
    if normalized_host and normalized_host in set(cfg.get("external_hosts", [])):
        return RUNTIME_ENV_EXTERNAL, "request_host"

    return RUNTIME_ENV_INTERNAL, "default_internal"


def set_request_runtime_environment(host: str | None):
    env, _ = resolve_runtime_environment(host)
    return _REQUEST_RUNTIME_ENV.set(env)


def reset_request_runtime_environment(token) -> None:
    _REQUEST_RUNTIME_ENV.reset(token)


def get_current_runtime_environment() -> str:
    env = _REQUEST_RUNTIME_ENV.get()
    if env in _SUPPORTED_RUNTIME_ENVS:
        return env
    inferred_env, _ = resolve_runtime_environment(None)
    return inferred_env


def get_visible_tool_keys() -> set[str]:
    cfg = load_tool_visibility_config()
    runtime_env = get_current_runtime_environment()
    if runtime_env == RUNTIME_ENV_EXTERNAL:
        keys = cfg.get("external_visible_tool_keys", [])
    else:
        keys = cfg.get("internal_visible_tool_keys", [])
    return {str(v).strip() for v in keys if str(v).strip()}


def is_tool_visible(tool_name: str | None) -> bool:
    name = (tool_name or "").strip()
    if not name:
        return False
    visible_keys = get_visible_tool_keys()
    if not visible_keys:
        return True
    return name in visible_keys

