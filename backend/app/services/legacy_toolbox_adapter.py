from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import copy
import concurrent.futures
import base64
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, TypeVar

import requests
from cryptography.fernet import Fernet, InvalidToken

from app.core.config_simple import SECRET_KEY


REQUEST_RETRIES = 3
REQUEST_BACKOFF_SECONDS = 1.0
SP_TOOL_CACHE_TTL_SECONDS = 180
VMP_COOKIE_CACHE_TTL_SECONDS = 180
ZONE_CREDENTIAL_CACHE_TTL_SECONDS = 120
DEFAULT_TOKEN_PRELOAD_TIMEOUT_SECONDS = 60
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
REQUEST_TIMEOUT_MIN_SECONDS = 1
REQUEST_TIMEOUT_MAX_SECONDS = 600


def _resolve_legacy_toolbox_dir() -> Path:
    dev_dir = Path(__file__).resolve().parents[3] / "ref" / "toolboxweb"
    candidates = [dev_dir]
    if getattr(sys, "frozen", False):
        runtime_root = Path(sys.executable).resolve().parent
        meipass = Path(getattr(sys, "_MEIPASS", runtime_root))
        candidates = [
            runtime_root / "toolboxweb",
            meipass / "toolboxweb",
            *candidates,
        ]
    for candidate in candidates:
        if (candidate / "vehicle_project_rule.py").exists():
            return candidate
    # Fallback to first candidate; subsequent imports will raise a clear error if missing
    return candidates[0]


LEGACY_TOOLBOX_DIR = _resolve_legacy_toolbox_dir()
ACCOUNT_PASSWORD_FILE = LEGACY_TOOLBOX_DIR / "static" / "config" / "account&password.json"
VEHICLE_RULE_OVERRIDE_FILE = LEGACY_TOOLBOX_DIR / "static" / "config" / "vehicle_project_rules.override.json"

if str(LEGACY_TOOLBOX_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_TOOLBOX_DIR))

logger = logging.getLogger("app.services.legacy_toolbox")
T = TypeVar("T")


def _mos_token_pool_use_db() -> bool:
    """为 1/true/yes 时，将 SP/Zone/VMP 等 token 缓存写入数据库，供多进程共享。"""
    return os.getenv("MOS_TOKEN_POOL_USE_DB", "1").strip().lower() in ("1", "true", "yes")


def _sp_tool_from_access_token(access_token: str) -> Any:
    from EnrollRequestManager import SPTool

    inst = object.__new__(SPTool)
    inst.access_token = access_token
    return inst


def _serialize_pool_value(key: str, value: Any) -> str:
    if key == "sp_tool":
        token = getattr(value, "access_token", "") or ""
        return json.dumps({"kind": "sp_tool", "access_token": token}, ensure_ascii=False)
    if key.startswith("zone_credentials:"):
        a, b = value
        return json.dumps({"kind": "zone_credentials", "a": a, "b": b}, ensure_ascii=False)
    if key == "vmp_cookies":
        return json.dumps({"kind": "vmp_cookies", "cookies": value}, ensure_ascii=False)
    raise ValueError(f"无法序列化 token 池项: {key}")


def _deserialize_pool_value(key: str, payload: str) -> Any:
    obj = json.loads(payload)
    kind = obj.get("kind")
    if kind == "sp_tool":
        return _sp_tool_from_access_token(str(obj.get("access_token") or ""))
    if kind == "zone_credentials":
        return (str(obj.get("a") or ""), str(obj.get("b") or ""))
    if kind == "vmp_cookies":
        return str(obj.get("cookies") or "")
    raise ValueError(f"无法反序列化 token 池项: {key}")


def _db_pool_get_with_expiry(key: str) -> tuple[Any, float] | None:
    from app.database import engine
    from app.models import MosTokenPoolEntry
    from sqlmodel import Session, select

    now = datetime.utcnow()
    with Session(engine) as session:
        row = session.exec(select(MosTokenPoolEntry).where(MosTokenPoolEntry.cache_key == key)).first()
        if not row or row.expires_at <= now:
            return None
        plain = _decrypt_secret(row.payload_enc)
        if not plain:
            return None
        try:
            value = _deserialize_pool_value(key, plain)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mos token pool 反序列化失败 key=%s: %s", key, exc)
            return None
        remaining = (row.expires_at - datetime.utcnow()).total_seconds()
        if remaining <= 0:
            return None
        exp_ts = time.time() + remaining
        return (value, exp_ts)


def _db_pool_put(key: str, value: Any, ttl_seconds: int) -> None:
    from app.database import engine
    from app.models import MosTokenPoolEntry
    from sqlmodel import Session, select

    plain = _serialize_pool_value(key, value)
    enc = _encrypt_secret(plain)
    expires_at = datetime.utcnow() + timedelta(seconds=max(1, int(ttl_seconds)))
    now = datetime.utcnow()
    with Session(engine) as session:
        row = session.exec(select(MosTokenPoolEntry).where(MosTokenPoolEntry.cache_key == key)).first()
        if row:
            row.payload_enc = enc
            row.expires_at = expires_at
            row.updated_at = now
            session.add(row)
        else:
            session.add(
                MosTokenPoolEntry(
                    cache_key=key,
                    payload_enc=enc,
                    expires_at=expires_at,
                    updated_at=now,
                )
            )
        session.commit()


def _db_pool_delete(key: str) -> None:
    from app.database import engine
    from app.models import MosTokenPoolEntry
    from sqlmodel import Session, select

    with Session(engine) as session:
        row = session.exec(select(MosTokenPoolEntry).where(MosTokenPoolEntry.cache_key == key)).first()
        if row:
            session.delete(row)
            session.commit()


def _db_pool_clear_all() -> None:
    if not _mos_token_pool_use_db():
        return
    from app.database import engine
    from app.models import MosTokenPoolEntry
    from sqlmodel import Session, select

    with Session(engine) as session:
        rows = session.exec(select(MosTokenPoolEntry)).all()
        for row in rows:
            session.delete(row)
        session.commit()


_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_INFLIGHT: dict[str, threading.Event] = {}
_CACHE_INFLIGHT_ERRORS: dict[str, Exception] = {}
_CACHE_METRICS: dict[str, dict[str, int]] = {}
_TOKEN_PRELOAD_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="mos-token-preload"
)
_TOKEN_PRELOAD_FUTURES: dict[str, concurrent.futures.Future[Any]] = {}
_TOKEN_PRELOAD_STATE: dict[str, dict[str, Any]] = {}
_TOKEN_PRELOAD_STATE_LOCK = threading.Lock()


def _touch_cache_metrics(key: str) -> dict[str, int]:
    metrics = _CACHE_METRICS.get(key)
    if metrics is None:
        metrics = {
            "requests": 0,
            "hits": 0,
            "misses": 0,
            "waits": 0,
            "errors": 0,
            "refreshes": 0,
        }
        _CACHE_METRICS[key] = metrics
    return metrics


def _mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 2:
        return "*" * len(value)
    return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"


def _load_account_password_json() -> dict[str, Any]:
    if not ACCOUNT_PASSWORD_FILE.exists():
        return {}
    try:
        return json.loads(ACCOUNT_PASSWORD_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read account/password config: %s", exc)
        return {}


def _build_fernet() -> Fernet:
    key_material = hashlib.sha256(SECRET_KEY.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)


def _encrypt_secret(value: str) -> str:
    token = _build_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def _decrypt_secret(value: str) -> str:
    try:
        plain = _build_fernet().decrypt(value.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken:
        return ""


def _get_password_plain(item: dict[str, Any]) -> str:
    encrypted = str(item.get("password_enc") or "").strip()
    if encrypted:
        decrypted = _decrypt_secret(encrypted)
        if decrypted:
            return decrypted
    return str(item.get("password") or "")


def _normalize_credentials_payload(raw: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for section in ["uat_mos_portal", "oa"]:
        item = raw.get(section) or {}
        normalized[section] = {
            "account": str(item.get("account") or ""),
            "password_enc": str(item.get("password_enc") or ""),
            "password": str(item.get("password") or ""),
        }
    return normalized


def _normalize_runtime_settings_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    item = raw or {}
    value = item.get("request_timeout_seconds")
    try:
        timeout_seconds = int(value)
    except (TypeError, ValueError):
        timeout_seconds = DEFAULT_REQUEST_TIMEOUT_SECONDS
    timeout_seconds = max(REQUEST_TIMEOUT_MIN_SECONDS, min(REQUEST_TIMEOUT_MAX_SECONDS, timeout_seconds))
    return {"request_timeout_seconds": timeout_seconds}


def get_runtime_settings() -> dict[str, Any]:
    raw = _load_account_password_json()
    return _normalize_runtime_settings_payload(raw.get("runtime"))


def get_runtime_credentials_masked() -> dict[str, Any]:
    raw = _normalize_credentials_payload(_load_account_password_json())
    result: dict[str, Any] = {}
    for section in ["uat_mos_portal", "oa"]:
        item = raw.get(section) or {}
        account = str(item.get("account") or "")
        password = _get_password_plain(item)
        result[section] = {
            "account": account,
            "password_masked": _mask_secret(password),
        }
    result["runtime"] = get_runtime_settings()
    return result


def update_runtime_credentials(
    *,
    uat_mos_portal_account: str | None = None,
    uat_mos_portal_password: str | None = None,
    oa_account: str | None = None,
    oa_password: str | None = None,
    request_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    payload = _normalize_credentials_payload(_load_account_password_json())
    payload.setdefault("uat_mos_portal", {})
    payload.setdefault("oa", {})

    if uat_mos_portal_account is not None:
        payload["uat_mos_portal"]["account"] = uat_mos_portal_account.strip()
    if uat_mos_portal_password is not None and uat_mos_portal_password.strip():
        payload["uat_mos_portal"]["password_enc"] = _encrypt_secret(uat_mos_portal_password.strip())
        payload["uat_mos_portal"]["password"] = ""
    if oa_account is not None:
        payload["oa"]["account"] = oa_account.strip()
    if oa_password is not None and oa_password.strip():
        payload["oa"]["password_enc"] = _encrypt_secret(oa_password.strip())
        payload["oa"]["password"] = ""

    runtime = _normalize_runtime_settings_payload(payload.get("runtime"))
    if request_timeout_seconds is not None:
        timeout_seconds = int(request_timeout_seconds)
        timeout_seconds = max(REQUEST_TIMEOUT_MIN_SECONDS, min(REQUEST_TIMEOUT_MAX_SECONDS, timeout_seconds))
        runtime["request_timeout_seconds"] = timeout_seconds
    payload["runtime"] = runtime

    ACCOUNT_PASSWORD_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACCOUNT_PASSWORD_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for _k in ("sp_tool", "vmp_cookies", "zone_credentials:uat", "zone_credentials:live"):
        _CACHE.pop(_k, None)
    try:
        _db_pool_clear_all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("mos token pool 清空数据库失败: %s", exc)
    return get_runtime_credentials_masked()


def _get_request_timeout_tuple() -> tuple[int, int]:
    timeout_seconds = int(get_runtime_settings()["request_timeout_seconds"])
    connect_timeout = min(10, timeout_seconds)
    return connect_timeout, timeout_seconds


def _default_vehicle_rules() -> list[dict[str, Any]]:
    from vehicle_project_rule import RULES

    return copy.deepcopy(RULES)


def _load_vehicle_rules() -> list[dict[str, Any]]:
    if VEHICLE_RULE_OVERRIDE_FILE.exists():
        try:
            raw = json.loads(VEHICLE_RULE_OVERRIDE_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return raw
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read vehicle rule override: %s", exc)
    return _default_vehicle_rules()


def _save_vehicle_rules(rules: list[dict[str, Any]]) -> None:
    VEHICLE_RULE_OVERRIDE_FILE.parent.mkdir(parents=True, exist_ok=True)
    VEHICLE_RULE_OVERRIDE_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def get_vehicle_rules_with_index() -> list[dict[str, Any]]:
    rows = _load_vehicle_rules()
    return [{"rule_index": idx, **row} for idx, row in enumerate(rows)]


def add_vehicle_rule(rule: dict[str, Any]) -> list[dict[str, Any]]:
    rules = _load_vehicle_rules()
    rules.append(rule)
    _save_vehicle_rules(rules)
    return get_vehicle_rules_with_index()


def bulk_add_vehicle_rules(new_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = _load_vehicle_rules()
    rules.extend(new_rules)
    _save_vehicle_rules(rules)
    return get_vehicle_rules_with_index()


def update_vehicle_rule(rule_index: int, rule: dict[str, Any]) -> list[dict[str, Any]]:
    rules = _load_vehicle_rules()
    if rule_index < 0 or rule_index >= len(rules):
        raise IndexError("rule_index out of range")
    rules[rule_index] = rule
    _save_vehicle_rules(rules)
    return get_vehicle_rules_with_index()


def delete_vehicle_rule(rule_index: int) -> list[dict[str, Any]]:
    rules = _load_vehicle_rules()
    if rule_index < 0 or rule_index >= len(rules):
        raise IndexError("rule_index out of range")
    del rules[rule_index]
    _save_vehicle_rules(rules)
    return get_vehicle_rules_with_index()


def _with_retry(desc: str, fn: Callable[[], T], retries: int = REQUEST_RETRIES) -> T:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= retries:
                break
            sleep_seconds = REQUEST_BACKOFF_SECONDS * attempt
            logger.warning("%s failed (%s/%s), retry in %ss: %s", desc, attempt, retries, sleep_seconds, exc)
            time.sleep(sleep_seconds)
    assert last_error is not None
    raise last_error


def _get_cached(key: str, ttl_seconds: int, loader: Callable[[], T], force_refresh: bool = False) -> T:
    while True:
        now = time.time()
        with _CACHE_LOCK:
            metrics = _touch_cache_metrics(key)
            metrics["requests"] += 1
            if not force_refresh:
                cached = _CACHE.get(key)
                if cached and cached[0] > now:
                    metrics["hits"] += 1
                    return cached[1]
            inflight = _CACHE_INFLIGHT.get(key)
            if inflight is None:
                inflight = threading.Event()
                _CACHE_INFLIGHT[key] = inflight
                is_owner = True
                if force_refresh:
                    metrics["refreshes"] += 1
            else:
                is_owner = False
                metrics["waits"] += 1

        if is_owner:
            if not force_refresh and _mos_token_pool_use_db():
                db_pair = _db_pool_get_with_expiry(key)
                if db_pair is not None:
                    value, exp_ts = db_pair
                    with _CACHE_LOCK:
                        _touch_cache_metrics(key)["hits"] += 1
                        _CACHE[key] = (exp_ts, value)
                        _CACHE_INFLIGHT_ERRORS.pop(key, None)
                        _CACHE_INFLIGHT.pop(key, None)
                        inflight.set()
                    return value
            with _CACHE_LOCK:
                _touch_cache_metrics(key)["misses"] += 1
            try:
                value = loader()
            except Exception as exc:  # noqa: BLE001
                with _CACHE_LOCK:
                    _touch_cache_metrics(key)["errors"] += 1
                    _CACHE_INFLIGHT_ERRORS[key] = exc
                    _CACHE_INFLIGHT.pop(key, None)
                    inflight.set()
                raise
            with _CACHE_LOCK:
                _CACHE[key] = (time.time() + ttl_seconds, value)
                _CACHE_INFLIGHT_ERRORS.pop(key, None)
                _CACHE_INFLIGHT.pop(key, None)
                inflight.set()
            if _mos_token_pool_use_db():
                try:
                    _db_pool_put(key, value, ttl_seconds)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("mos token pool 写入数据库失败 key=%s: %s", key, exc)
            return value

        inflight.wait()
        with _CACHE_LOCK:
            err = _CACHE_INFLIGHT_ERRORS.get(key)
            if err is not None:
                raise err


def _cache_expires_in_seconds(key: str) -> int:
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached:
            remaining = int(cached[0] - time.time())
            if remaining > 0:
                return remaining
    if _mos_token_pool_use_db():
        from app.database import engine
        from app.models import MosTokenPoolEntry
        from sqlmodel import Session, select

        with Session(engine) as session:
            row = session.exec(select(MosTokenPoolEntry).where(MosTokenPoolEntry.cache_key == key)).first()
            if row and row.expires_at > datetime.utcnow():
                return max(0, int((row.expires_at - datetime.utcnow()).total_seconds()))
    return 0


def _cache_metrics_snapshot(key: str) -> dict[str, int]:
    with _CACHE_LOCK:
        current = _touch_cache_metrics(key)
        return dict(current)


def _http_get(url: str, params: dict[str, Any]) -> requests.Response:
    def _do() -> requests.Response:
        response = requests.get(url, params=params, timeout=_get_request_timeout_tuple())
        response.raise_for_status()
        return response

    return _with_retry(f"GET {url}", _do)


def _get_sp_tool():
    from EnrollRequestManager import SPTool

    return _get_cached("sp_tool", SP_TOOL_CACHE_TTL_SECONDS, SPTool)


def _refresh_sp_tool():
    from EnrollRequestManager import SPTool

    return _get_cached("sp_tool", SP_TOOL_CACHE_TTL_SECONDS, SPTool, force_refresh=True)


def _get_vmp_cookies() -> str:
    from VMP_Config import web_driver_get_vmp_cookies

    return _get_cached("vmp_cookies", VMP_COOKIE_CACHE_TTL_SECONDS, web_driver_get_vmp_cookies)


def _get_zone_credentials(env: str) -> tuple[str, str]:
    if env == "uat":
        from Zone_token_getter import web_driver_get_zone_token_cookies as get_cookies
    else:
        from Live_Zone_token_getter import web_driver_get_zone_live_token_cookies as get_cookies

    key = f"zone_credentials:{env}"
    return _get_cached(key, ZONE_CREDENTIAL_CACHE_TTL_SECONDS, get_cookies)


def _refresh_zone_credentials(env: str) -> tuple[str, str]:
    if env == "uat":
        from Zone_token_getter import web_driver_get_zone_token_cookies as get_cookies
    else:
        from Live_Zone_token_getter import web_driver_get_zone_live_token_cookies as get_cookies

    key = f"zone_credentials:{env}"
    return _get_cached(key, ZONE_CREDENTIAL_CACHE_TTL_SECONDS, get_cookies, force_refresh=True)


def _load_zone_uat(force_refresh: bool = False) -> tuple[str, str]:
    return _refresh_zone_credentials("uat") if force_refresh else _get_zone_credentials("uat")


def _load_zone_live(force_refresh: bool = False) -> tuple[str, str]:
    return _refresh_zone_credentials("live") if force_refresh else _get_zone_credentials("live")


def _load_sp_tool(force_refresh: bool = False) -> Any:
    return _refresh_sp_tool() if force_refresh else _get_sp_tool()


def _load_vmp_cookies(force_refresh: bool = False) -> str:
    if force_refresh:
        from VMP_Config import web_driver_get_vmp_cookies

        return _get_cached("vmp_cookies", VMP_COOKIE_CACHE_TTL_SECONDS, web_driver_get_vmp_cookies, force_refresh=True)
    return _get_vmp_cookies()


TOKEN_PRELOAD_SCOPES = {
    "zone-uat": {
        "cache_key": "zone_credentials:uat",
        "ttl": ZONE_CREDENTIAL_CACHE_TTL_SECONDS,
        "loader": _load_zone_uat,
        "features": [
            "x509-cert(env=uat)",
            "uat-af-dp-query",
            "uat-vehicle-import(target=afdp)",
        ],
        "label": "Zone UAT Token/Cookies",
    },
    "zone-live": {
        "cache_key": "zone_credentials:live",
        "ttl": ZONE_CREDENTIAL_CACHE_TTL_SECONDS,
        "loader": _load_zone_live,
        "features": ["x509-cert(env=live)"],
        "label": "Zone LIVE Token/Cookies",
    },
    "sp-tool": {
        "cache_key": "sp_tool",
        "ttl": SP_TOOL_CACHE_TTL_SECONDS,
        "loader": _load_sp_tool,
        "features": ["uat-sp-query", "uat-vehicle-import(target=sp)"],
        "label": "SPTool Access Token",
    },
    "vmp-cookies": {
        "cache_key": "vmp_cookies",
        "ttl": VMP_COOKIE_CACHE_TTL_SECONDS,
        "loader": _load_vmp_cookies,
        "features": ["uat-vehicle-import(target=cdp)"],
        "label": "VMP Cookies",
    },
}


def _set_token_scope_state(scope: str, **updates: Any) -> None:
    now = datetime.utcnow().isoformat()
    with _TOKEN_PRELOAD_STATE_LOCK:
        state = _TOKEN_PRELOAD_STATE.setdefault(
            scope,
            {
                "scope": scope,
                "status": "idle",
                "label": TOKEN_PRELOAD_SCOPES.get(scope, {}).get("label", scope),
                "features": TOKEN_PRELOAD_SCOPES.get(scope, {}).get("features", []),
                "started_at": None,
                "finished_at": None,
                "last_error": None,
                "cache_expires_in_seconds": _cache_expires_in_seconds(
                    TOKEN_PRELOAD_SCOPES.get(scope, {}).get("cache_key", scope)
                ),
                "updated_at": now,
            },
        )
        state.update(updates)
        state["updated_at"] = now


def _run_token_scope_loader(scope: str, force_refresh: bool = False) -> Any:
    spec = TOKEN_PRELOAD_SCOPES[scope]
    _set_token_scope_state(scope, status="loading", started_at=datetime.utcnow().isoformat(), last_error=None)
    try:
        value = spec["loader"](force_refresh)  # type: ignore[misc]
        _set_token_scope_state(
            scope,
            status="ready",
            finished_at=datetime.utcnow().isoformat(),
            cache_expires_in_seconds=_cache_expires_in_seconds(spec["cache_key"]),
            last_error=None,
        )
        return value
    except Exception as exc:  # noqa: BLE001
        _set_token_scope_state(
            scope,
            status="error",
            finished_at=datetime.utcnow().isoformat(),
            cache_expires_in_seconds=0,
            last_error=str(exc),
        )
        raise


def _start_scope_preload(scope: str, force_refresh: bool = False) -> concurrent.futures.Future[Any]:
    with _TOKEN_PRELOAD_STATE_LOCK:
        future = _TOKEN_PRELOAD_FUTURES.get(scope)
        if future is not None and not future.done():
            return future
        future = _TOKEN_PRELOAD_EXECUTOR.submit(_run_token_scope_loader, scope, force_refresh)
        _TOKEN_PRELOAD_FUTURES[scope] = future
        return future


def preload_mos_tokens(
    *,
    scopes: list[str] | None = None,
    wait: bool = False,
    timeout_seconds: int = DEFAULT_TOKEN_PRELOAD_TIMEOUT_SECONDS,
    force_refresh: bool = False,
) -> dict[str, Any]:
    scope_list = scopes or list(TOKEN_PRELOAD_SCOPES.keys())
    invalid = [scope for scope in scope_list if scope not in TOKEN_PRELOAD_SCOPES]
    if invalid:
        raise ValueError(f"未知 token scope: {', '.join(invalid)}")
    if timeout_seconds <= 0:
        timeout_seconds = DEFAULT_TOKEN_PRELOAD_TIMEOUT_SECONDS

    metrics_before = {
        scope: _cache_metrics_snapshot(TOKEN_PRELOAD_SCOPES[scope]["cache_key"])
        for scope in scope_list
    }
    futures: dict[str, concurrent.futures.Future[Any]] = {}
    for scope in scope_list:
        futures[scope] = _start_scope_preload(scope, force_refresh=force_refresh)

    errors: dict[str, str] = {}
    if wait:
        deadline = time.time() + timeout_seconds
        for scope, future in futures.items():
            remaining = max(1.0, deadline - time.time())
            try:
                future.result(timeout=remaining)
            except Exception as exc:  # noqa: BLE001
                errors[scope] = str(exc)

    with _TOKEN_PRELOAD_STATE_LOCK:
        items: list[dict[str, Any]] = []
        for scope in scope_list:
            spec = TOKEN_PRELOAD_SCOPES[scope]
            state = dict(_TOKEN_PRELOAD_STATE.get(scope) or {})
            if not state:
                state = {
                    "scope": scope,
                    "status": "idle",
                    "label": spec["label"],
                    "features": spec["features"],
                    "started_at": None,
                    "finished_at": None,
                    "last_error": None,
                }
            state["cache_expires_in_seconds"] = _cache_expires_in_seconds(spec["cache_key"])
            metrics_after = _cache_metrics_snapshot(spec["cache_key"])
            before = metrics_before.get(scope, {})
            delta_hits = metrics_after.get("hits", 0) - int(before.get("hits", 0))
            delta_waits = metrics_after.get("waits", 0) - int(before.get("waits", 0))
            delta_misses = metrics_after.get("misses", 0) - int(before.get("misses", 0))
            if delta_waits > 0:
                pool_event = "等待复用"
            elif delta_hits > 0:
                pool_event = "命中缓存"
            elif delta_misses > 0:
                pool_event = "新建加载"
            else:
                pool_event = "无变化"
            future = futures.get(scope)
            inflight = bool(future is not None and not future.done())
            state["pool_event"] = pool_event
            state["pool_inflight"] = inflight
            state["pool_stats"] = metrics_after
            if scope in errors:
                state["last_error"] = errors[scope]
            items.append(state)

    return {
        "started": True,
        "waited": wait,
        "timeout_seconds": timeout_seconds,
        "items": items,
        "has_errors": bool(errors),
        "errors": errors,
    }


def query_unicom_sim(project: str, search_value: str) -> Any:
    def _do() -> requests.Response:
        response = requests.get(
            "http://47.116.180.173:5000/JasperGetter/SIMData",
            params={"project": project, "search_value": search_value},
            timeout=_get_request_timeout_tuple(),
        )
        response.raise_for_status()
        return response

    # 联通接口首次调用常因下游预热较慢，单次超时提升至 3 分钟且不重试，避免总时长失控。
    response = _with_retry("GET unicom SIM data", _do, retries=1)
    try:
        return response.json()
    except ValueError:
        return response.text


def query_ctcc_sim(iccid: str | None, msisdn: str | None, imsi: str | None) -> dict[str, Any]:
    from AFC_SIMCard_Serach import search_sim_data

    result = search_sim_data(iccid=iccid, msisdn=msisdn, imsi=imsi)
    return {"success": result.get("success", False), "data": result.get("data")}


def query_uat_af_dp(vin: str | None, zxdsn: str | None, iamsn: str | None, iccid: str | None) -> dict[str, Any]:
    from uat_af_dp_congif_set import uat_af_dp_data_read

    result = uat_af_dp_data_read(vin=vin, zxdsn=zxdsn, iamsn=iamsn, iccid=iccid)
    return {"success": result.get("success", False), "data": result.get("data")}


def query_uat_sp_vehicle(vin: str) -> dict[str, Any]:
    spt = _get_sp_tool()
    result = spt.get_sp_details(vin, "vw")
    if isinstance(result, str) and "后台错误" in result:
        spt = _refresh_sp_tool()
        result = spt.get_sp_details(vin, "vw")
    if isinstance(result, str):
        if "后台错误" in result:
            return {"success": False, "data": result}
        if result == "车辆未找到！":
            return {"success": False, "data": f"VIN: {vin} 的车辆数据不存在"}
    return {"success": True, "data": result}


def bind_uat_enrollment(vin: str, phone: str) -> dict[str, Any]:
    spt = _get_sp_tool()
    code, result = spt.bind_puser(phone, vin, "vw")
    if code == 1:
        return {"success": True, "data": result}
    if code == 0:
        return {"success": False, "data": result}
    if code == 2:
        spt = _refresh_sp_tool()
        code, result = spt.bind_puser(phone, vin, "vw")
        return {"success": code == 1, "data": result}
    return {"success": False, "data": result}


def unbind_uat_enrollment(vin: str) -> dict[str, Any]:
    spt = _get_sp_tool()
    code, result = spt.unbind_puser(vin, "vw")
    if code == 1:
        return {"success": True, "data": result}
    if code == 0:
        return {"success": False, "data": result}
    if code == 2:
        spt = _refresh_sp_tool()
        code, result = spt.unbind_puser(vin, "vw")
        return {"success": code == 1, "data": result}
    return {"success": False, "data": result}


def import_uat_vehicle_config(target: str, check_duplicated: bool, vehicle_data: dict[str, Any]) -> dict[str, Any]:
    from VMP_Config import web_driver_get_vmp_cookies, query_vehicle_info, set_vmp_data
    from uat_af_dp_congif_set import uat_af_dp_data_read, uat_af_dp_config_set

    vin = vehicle_data.get("车辆VIN码")
    if not vin:
        return {"success": False, "data": "车辆VIN码不能为空"}

    if target == "sp":
        if vehicle_data.get("项目版本号") in {"MOS_A_NB_Low", "MOS_A_NB_High"}:
            vehicle_data["项目版本号"] = "MOS_A_NB"
        spt = _get_sp_tool()
        exists = spt.get_sp_details(vin, "vw")
        if exists != "车辆未找到！" and check_duplicated:
            return {"success": False, "data": f"{vin}车辆信息在后台存在!"}
        response = spt.vehicle_test_data_file_processor("vw", vehicle_data)
        return {"success": True, "data": response}

    if target == "cdp":
        cookies = _get_vmp_cookies()
        status_vehicle, result_vehicle = query_vehicle_info("vin", vin, cookies)
        if status_vehicle and check_duplicated:
            return {"success": False, "data": f"{vin}车辆信息在后台存在!"}
        if (not status_vehicle) and result_vehicle != "未在车辆管理平台登记,请联系管理员":
            cookies = _get_cached("vmp_cookies", VMP_COOKIE_CACHE_TTL_SECONDS, web_driver_get_vmp_cookies, force_refresh=True)
            status_vehicle, result_vehicle = query_vehicle_info("vin", vin, cookies)
            if status_vehicle and check_duplicated:
                return {"success": False, "data": f"{vin}车辆信息在后台存在!"}
            if (not status_vehicle) and result_vehicle != "未在车辆管理平台登记,请联系管理员":
                return {"success": False, "data": f"检查车辆重复值异常:{result_vehicle}"}
        response = set_vmp_data(vehicle_data, cookies)
        return {"success": True, "data": response}

    if target == "afdp":
        check_result = uat_af_dp_data_read(vin=vin).get("data")
        if check_result != f"UAT AF DP主数据平台未找到{vin}！" and check_duplicated:
            return {"success": False, "data": f"{vin}车辆信息在后台存在!"}
        status, response = uat_af_dp_config_set(vehicle_data)
        return {"success": bool(status), "data": response}

    return {"success": False, "data": f"未知导入目标: {target}"}


def generate_uat_vehicle_import_data(
    project: str,
    car_software_version: str,
    hu_fazit_id: str,
    ocu_iccid: str,
    msisdn: str,
    ocu_fazit_id: str,
    vehicle_vin: str,
    application_department: str,
) -> dict[str, Any]:
    from vehicle_project_rule import VehicleConfigError, generate_vehicle_config_data

    try:
        import vehicle_project_rule as vehicle_rule_module

        vehicle_rule_module.RULES = _load_vehicle_rules()
        data = generate_vehicle_config_data(
            project=project,
            car_software_version=car_software_version,
            hu_fazit_id=hu_fazit_id,
            ocu_iccid=ocu_iccid,
            msisdn=msisdn,
            ocu_fazit_id=ocu_fazit_id,
            vehicle_vin=vehicle_vin,
            application_department=application_department,
        )
        return {"success": True, "data": data}
    except VehicleConfigError as exc:
        return {"success": False, "data": str(exc)}


def list_uat_vehicle_config_rules() -> dict[str, Any]:
    version_patterns_by_project: dict[str, set[str]] = {}
    for rule in _load_vehicle_rules():
        project = str(rule.get("项目版本号", "")).strip()
        if not project:
            continue
        patterns = rule.get("车机软件版本号") or []
        if not isinstance(patterns, list):
            continue
        if project not in version_patterns_by_project:
            version_patterns_by_project[project] = set()
        for pattern in patterns:
            value = str(pattern).strip().upper()
            if value:
                version_patterns_by_project[project].add(value)

    projects = sorted(version_patterns_by_project.keys())
    return {
        "projects": projects,
        "version_patterns_by_project": {
            project: sorted(version_patterns_by_project[project])
            for project in projects
        },
    }


def handle_x509_feature(
    action: str,
    env: str,
    iam_sns: list[str] | None = None,
    csrs: list[str] | None = None,
    csr: str | None = None,
    cert: str | None = None,
) -> dict[str, Any]:
    from parse_csr_hex import parse_csr_hex, parse_x509_hex_certificate

    if action == "parse_csr":
        return {"success": True, "data": parse_csr_hex(csr or "")}
    if action == "parse_cert":
        return {"success": True, "data": parse_x509_hex_certificate(cert or "")}

    if env == "uat":
        from iam_x509_signature import iam_x509_cert_sign, get_x509_cert_by_sn

        sign_func = iam_x509_cert_sign
        check_func = get_x509_cert_by_sn
    else:
        from Live_iam_x509_signature import live_iam_x509_cert_sign, live_get_x509_cert_by_sn

        sign_func = live_iam_x509_cert_sign
        check_func = live_get_x509_cert_by_sn

    zone_token, cookies = _get_zone_credentials(env)

    def _run_with_zone_retry(callable_fn: Callable[[str, str, str], tuple[bool, dict[str, Any]]], value: str) -> dict[str, Any]:
        nonlocal zone_token, cookies
        try:
            _status, result = callable_fn(value, zone_token, cookies)
            return result
        except Exception:  # noqa: BLE001
            zone_token, cookies = _refresh_zone_credentials(env)
            _status, result = callable_fn(value, zone_token, cookies)
            return result

    if action == "check":
        results: list[dict[str, Any]] = []
        for sn in iam_sns or []:
            results.append(_run_with_zone_retry(check_func, sn))
        return {"success": True, "data": results}

    if action == "sign":
        results = []
        for item in csrs or []:
            results.append(_run_with_zone_retry(sign_func, item))
        return {"success": True, "data": results}

    return {"success": False, "data": f"未知 action: {action}"}
