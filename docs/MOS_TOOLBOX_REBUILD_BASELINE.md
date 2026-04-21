# MOS工具箱重构基线（已收敛范围）

> **文档索引**：`docs/README.md` · **宿主与插件总览**：`docs/PROJECT_AND_AGENT_GUIDE.md`

> 状态：已确认（用户选择：**单工具模式** + **UAT/LIVE 合并页环境切换**）
> 目标：将 `ref/toolboxweb` 老工具按当前项目规范重构并集成。

## 1. 保留能力（仅这 6 类）

1. IAM X509 证书查询/签发/解析（UAT + Live）
2. CEI DP 数据查询（UAT + Live）
3. SIM 卡信息查询（联通 + 电信）
4. UAT AF DP 数据查询
5. UAT SP 后台信息查询
6. UAT 车辆配置数据导入

其余历史能力全部不接入新版本。

## 2. 新系统呈现方式

- 工具形态：**单工具**（一个 `tool_id`）
- 使用页：`/tools/:toolId` 下一个业务面板，分多个 Tab
- 环境切换：同类能力统一页面内通过 `env`（`uat` / `live`）切换
- 管理页：沿用现有 `ToolManage` 的「通用管理」；如无额外业务治理需求，不新增管理 Tab

## 3. 审计兼容（硬约束）

所有业务接口路径必须满足：

`/api/v1/tools/{tool_id}/features/{feature}`

其中 `{feature}` 为 **`/features/` 之后的整段路径**（与 `backend/main.py` 中 `TOOL_FEATURE_REGEX` 一致），字符集为 **`[a-zA-Z0-9_/-]+`**：可以是单层 slug（如 `x509-cert`），也可以是多段嵌套（如 `mos-manage/vehicle-rules`）。`tool.manifest.json` 的 `feature_slugs` / `behavior_catalog.key` 及 `Tool.behavior_catalog_json` 须与真实路由同步，以便 `APIAccessLog` 关联 `tool_id` / `feature_name` 并解析 **中文行为名**。

## 4. 功能 slug 规划

- `x509-cert`：IAM X509（查询/签发/CSR解析/证书解析）
- `cei-dp-query`：CEI DP 查询
- `sim-query`：SIM 查询（联通 + 电信）
- `uat-af-dp-query`：UAT AF DP 查询
- `uat-sp-query`：UAT SP 查询
- `uat-vehicle-import`：UAT 车辆配置导入

## 5. 后端接口契约（v1）

> 约定：统一返回 `{ success, message, data }`；异常时返回标准 HTTP 状态码 + 说明。

### 5.1 IAM X509（x509-cert）

- `POST /api/v1/tools/{tool_id}/features/x509-cert`
  - 入参：
    - 查询：`{ action: "check", env: "uat" | "live", iam_sns: string[] }`
    - 签发：`{ action: "sign", env: "uat" | "live", csrs: string[] }`
    - 解析CSR：`{ action: "parse_csr", env: "uat" | "live", csr: string }`
    - 解析证书：`{ action: "parse_cert", env: "uat" | "live", cert: string }`
  - 出参：`{ success, data }`

### 5.2 CEI DP 查询（cei-dp-query）

- `GET /api/v1/tools/{tool_id}/features/cei-dp-query`
  - 查询参数：`env=uat|live&vin=<17位VIN>`
  - 出参：`{ success, data: object }`

### 5.3 SIM 查询（sim-query）

- `POST /api/v1/tools/{tool_id}/features/sim-query`
  - 入参：
    - 联通：`{ provider: "unicom", project: string, search_value: string }`
    - 电信：`{ provider: "ctcc", iccid?: string, msisdn?: string, imsi?: string }`
  - 出参：`{ success, data }`

### 5.4 UAT AF DP 查询（uat-af-dp-query）

- `POST /api/v1/tools/{tool_id}/features/uat-af-dp-query`
  - 入参：`{ vin?: string, zxdsn?: string, iamsn?: string, iccid?: string }`
  - 出参：`{ success, data: object }`

### 5.5 UAT SP 查询（uat-sp-query）

- `POST /api/v1/tools/{tool_id}/features/uat-sp-query`
  - 入参：`{ action: "vehicle" | "service_list", vin: string }`
  - 出参：`{ success, data }`

### 5.6 UAT 车辆配置导入（uat-vehicle-import）

- `POST /api/v1/tools/{tool_id}/features/uat-vehicle-import`
  - 入参：
    - `target`: `"sp" | "cdp" | "afdp"`
    - `check_duplicated`: `boolean`
    - `vehicle_data`: `object`
  - 出参：`{ success, data: object|string }`

## 6. 前端页面结构（单工具面板）

建议 Tab（Element Plus `el-tabs`）：

1. `IAM X509`
2. `CEI DP`
3. `SIM 查询`
4. `UAT AF DP`
5. `UAT SP 查询`
6. `UAT 车辆配置导入`

通用交互：

- 同类 UAT/LIVE 用 `el-segmented` 或 `el-radio-group` 切换
- 长耗时请求显示 loading 与超时提示
- 响应支持 JSON 查看与下载（按能力需要）

## 7. 稳定性/性能基线要求

- 所有外部请求设置 timeout，区分连接超时与读取超时
- 对 Selenium/token 获取流程增加缓存与失效重试
- 统一异常包装，避免把 Python 原始异常直接透出前端
- 批量接口支持逐项结果，不因单条失败中断全量
- 能分页的列表一律分页（遵循项目规范）

## 8. 实施顺序（执行计划）

1. 新增工具种子与前端显示名（单工具）
2. 后端新增 6 组 feature API（先通路后细节）
3. 前端新增单工具业务面板与 6 个 Tab（先跑通）
4. 分能力逐一迁移老逻辑并回归
5. 集成到管理页通用治理（授权、日志、反馈）
6. 按打包流程产出可运行包（考虑内网依赖与说明）

---

本文件是后续代码改造的执行基线，若需求变更以用户最新指令为准。
