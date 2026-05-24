import json
import os

from fastapi import APIRouter

from app.schemas import ToolVersionMetaResponse

router = APIRouter()


def _version_meta_from_env() -> ToolVersionMetaResponse:
    version = str(os.getenv("TOOLBOX_VERSION") or "0.0.0").strip() or "0.0.0"
    spec_revision = str(os.getenv("TOOLBOX_SPEC_REVISION") or "").strip() or None
    title = str(os.getenv("TOOLBOX_VERSION_TITLE") or "工具版本更新").strip() or "工具版本更新"
    raw = str(os.getenv("TOOLBOX_CHANGELOG") or "").strip()
    if not raw:
        raw = "本次发布未提供详细变更说明。"
    if raw.startswith("[") and raw.endswith("]"):
        try:
            rows = json.loads(raw)
            if isinstance(rows, list):
                lines = [str(x).strip() for x in rows if str(x).strip()]
                if lines:
                    raw = "\n".join(f"- {line}" for line in lines)
        except Exception:
            pass
    return ToolVersionMetaResponse(
        version=version,
        spec_revision=spec_revision,
        title=title,
        changelog=raw,
    )


@router.get("/meta/version", response_model=ToolVersionMetaResponse)
async def get_meta_version():
    return _version_meta_from_env()


@router.get("/version", response_model=ToolVersionMetaResponse)
async def get_version():
    return _version_meta_from_env()
