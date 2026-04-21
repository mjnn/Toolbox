"""
MOS 集成工具箱 API 冒烟测试（不依赖内网；网络类 502/504 视为通过）。
运行：在 backend 目录执行
  .venv\\Scripts\\python.exe scripts\\smoke_mos_toolbox.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
os.chdir(BACKEND)
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

NETWORK_OK = {502, 504, 408}

# 联通 SIM 单次可能长达 3 分钟；默认跳过，设置 MOS_SMOKE_INCLUDE_UNICOM=1 可测
INCLUDE_UNICOM = os.environ.get("MOS_SMOKE_INCLUDE_UNICOM", "").strip() in ("1", "true", "yes")
# UAT AF DP 需 Selenium 打开内网；外网环境易 TLS/超时，默认跳过，设 MOS_SMOKE_INCLUDE_SELENIUM=1 可测
INCLUDE_SELENIUM = os.environ.get("MOS_SMOKE_INCLUDE_SELENIUM", "").strip() in ("1", "true", "yes")


def _ok(name: str, status: int, text: str) -> None:
    if status >= 500 and status not in NETWORK_OK:
        raise SystemExit(f"FAIL {name}: HTTP {status}\n{text[:2000]}")


def main() -> None:
    client = TestClient(app)

    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    if r.status_code != 200:
        raise SystemExit(f"login failed: {r.status_code} {r.text}")
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    tr = client.get("/api/v1/tools/", params={"search": "mos-integration"})
    if tr.status_code != 200:
        raise SystemExit(f"list tools: {tr.status_code} {tr.text}")
    tools = tr.json()
    mos = next((t for t in tools if t.get("name") == "mos-integration-toolbox"), None)
    if not mos:
        raise SystemExit(f"mos-integration-toolbox not in tools: {tools}")
    tid = mos["id"]

    # 本地解析 CSR（不访问内网）
    r = client.post(
        f"/api/v1/tools/{tid}/features/x509-cert",
        headers=h,
        json={"action": "parse_csr", "env": "uat", "csr": "deadbeef"},
    )
    _ok("x509_parse_csr", r.status_code, r.text)
    if r.status_code != 200:
        raise SystemExit(f"x509_parse_csr unexpected {r.status_code}")

    # CEI DP（通常内网）
    r = client.get(
        f"/api/v1/tools/{tid}/features/cei-dp-query",
        headers=h,
        params={"env": "uat", "vin": "LSVAA4182E2184841"},
    )
    _ok("cei_dp", r.status_code, r.text)

    # 联通 SIM（慢；默认跳过）
    if INCLUDE_UNICOM:
        r = client.post(
            f"/api/v1/tools/{tid}/features/sim-query",
            headers=h,
            json={"provider": "unicom", "project": "CEI", "search_value": "test"},
        )
        _ok("sim_unicom", r.status_code, r.text)

    # 电信 SIM（本地目录或明确错误信息）
    r = client.post(
        f"/api/v1/tools/{tid}/features/sim-query",
        headers=h,
        json={"provider": "ctcc", "iccid": "89860000000000000000"},
    )
    _ok("sim_ctcc", r.status_code, r.text)
    if r.status_code != 200:
        raise SystemExit(f"sim_ctcc unexpected {r.status_code}")

    # UAT AF DP（Selenium + 内网；默认跳过）
    if INCLUDE_SELENIUM:
        r = client.post(
            f"/api/v1/tools/{tid}/features/uat-af-dp-query",
            headers=h,
            json={"vin": "LSVAA4182E2184841"},
        )
        _ok("uat_af_dp", r.status_code, r.text)

    # UAT Enrollment 查询（需账号文件，内网登录）
    r = client.post(
        f"/api/v1/tools/{tid}/features/uat-sp-query",
        headers=h,
        json={"action": "query_sp_info", "vin": "LSVAA4182E2184841"},
    )
    _ok("uat_sp_query", r.status_code, r.text)

    # 车辆规则
    r = client.get(
        f"/api/v1/tools/{tid}/features/uat-vehicle-config-rules",
        headers=h,
    )
    _ok("uat_vehicle_config_rules", r.status_code, r.text)
    if r.status_code != 200:
        raise SystemExit(f"uat_vehicle_config_rules {r.status_code} {r.text}")

    # 车辆配置生成（纯规则，无网络）
    r = client.post(
        f"/api/v1/tools/{tid}/features/uat-vehicle-config-generate",
        headers=h,
        json={
            "project": "MOS3_GP",
            "car_software_version": "01XX",
            "hu_fazit_id": "HFAZIT1",
            "ocu_iccid": "89860000000000000001",
            "msisdn": "13800138000",
            "ocu_fazit_id": "OFAZIT1",
            "vehicle_vin": "LSVAA4182E2184841",
            "application_department": "测试部",
        },
    )
    _ok("uat_vehicle_config_generate", r.status_code, r.text)
    if r.status_code != 200:
        raise SystemExit(f"uat_vehicle_config_generate {r.status_code} {r.text}")

    # MOS 管理（超管）
    for name, path in [
        ("mos_vehicle_rules", f"/api/v1/tools/{tid}/features/mos-manage/vehicle-rules"),
        ("mos_runtime_credentials", f"/api/v1/tools/{tid}/features/mos-manage/runtime-credentials"),
        ("mos_change_logs", f"/api/v1/tools/{tid}/features/mos-manage/change-logs"),
    ]:
        r = client.get(path, headers=h)
        _ok(name, r.status_code, r.text)
        if r.status_code != 200:
            raise SystemExit(f"{name} {r.status_code} {r.text}")

    # 批量预校验：单条合法规则
    sample_rule = {
        "项目版本号": "MOS3_GP",
        "OCU类型": "Conmod5G",
        "品牌": "VW",
        "车机类型": "CNS3.0",
        "燃油类型": "FV",
        "车机软件版本号": ["01XX"],
        "PRNR": "~28DK",
        "发电机号": "空",
        "运营商": "CUSC",
        "产线平台": "MQB_37WBaseline",
        "HU零件号": "3JD035866",
        "OCU零件号": "3JD035741",
    }
    r = client.post(
        f"/api/v1/tools/{tid}/features/mos-manage/vehicle-rules/bulk-import",
        headers=h,
        json={"rules": [sample_rule], "dry_run": True},
    )
    _ok("bulk_import_dry", r.status_code, r.text)
    if r.status_code != 200:
        raise SystemExit(f"bulk_import_dry {r.status_code} {r.text}")

    print("smoke_mos_toolbox: OK (network-dependent calls may be 502/504)")


if __name__ == "__main__":
    main()
