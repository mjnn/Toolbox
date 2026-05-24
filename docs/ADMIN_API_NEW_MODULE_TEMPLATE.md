# Admin 子模块新增模板

## 适用场景

当 `admin` 域出现新能力（新路由组）时，不要继续堆到 `admin.py`，而是新增独立模块。

## 目录与命名

- 文件路径：`backend/app/api/v1/admin_<domain>.py`
- 推荐示例：
  - `admin_feedback.py`
  - `admin_audit.py`
  - `admin_permissions.py`
  - `admin_tool_access.py`
  - `admin_releases.py`

## 代码骨架

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.api.v1.users import get_current_active_user

router = APIRouter()

@router.get("/your/path")
async def your_handler(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_session),
):
    ...
```

## 共享能力复用

优先使用 `backend/app/api/v1/admin_common.py`：

- `get_role_by_name`
- `user_is_tool_owner`
- `ensure_tool_governance`
- `ensure_permission_reviewer`
- `recipient_user_ids_for_tool`

禁止在新模块内重复定义以上逻辑。

## 路由注册

在 `backend/app/api/v1/api.py` 增加：

```python
from app.api.v1 import admin_<domain>
api_router.include_router(admin_<domain>.router, prefix="/admin", tags=["admin"])
```

## 合并前检查

- `python -m compileall backend/app/api/v1/*.py`
- `powershell -File scripts/run-ci-tool-checks.ps1`
- 确认未产生重复路由（旧模块中已删除迁出的同路径路由）
