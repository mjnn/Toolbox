"""根据展示名称生成项目空间 / 问卷 / 生命周期字段 / 分类树等标识（蛇形小写）。"""
from __future__ import annotations

import re
from typing import Literal

from pypinyin import Style, lazy_pinyin

IdentifierKeyTarget = Literal["space_key", "question_key", "lifecycle_field_key", "taxonomy_node_key"]

_DIGITS_ONLY = re.compile(r"^\d+$")


def _snake_from_ascii_chunk(s: str) -> str:
    t = (s or "").strip()
    if not t:
        return ""
    if _DIGITS_ONLY.fullmatch(t):
        return t
    t = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", t)
    t = t.replace("-", "_").replace(" ", "_")
    t = t.lower()
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def _finalize_lifecycle_key(key: str) -> str:
    key = (key or "").lower()
    key = re.sub(r"[^a-z0-9_]+", "_", key)
    key = re.sub(r"_+", "_", key).strip("_")
    if not key:
        key = "item"
    if not key[0].isalpha():
        key = "k_" + key
    return key[:64]


def _finalize_general_key(key: str) -> str:
    key = (key or "").lower()
    key = re.sub(r"[^a-z0-9_-]+", "_", key)
    key = re.sub(r"_+", "_", key).strip("_-")
    if not key:
        key = "item"
    return key[:64]


def suggest_identifier_key(source_text: str, target: IdentifierKeyTarget) -> str:
    """
    规则概要：
    - 展示名整段为数字：原样保留（生命周期字段 key 会加 ``k_`` 前缀以满足小写字母开头）。
    - 含中文：中文片段转拼音后以小写蛇形拼接；英文片段按蛇形格式化。
    - 纯英文/混合拉丁：转小写蛇形（驼峰、空格、连字符参与分词）。
    """
    raw = (source_text or "").strip()
    if not raw:
        return ""
    if _DIGITS_ONLY.fullmatch(raw):
        if target == "lifecycle_field_key":
            return _finalize_lifecycle_key(raw)
        return _finalize_general_key(raw)

    pieces: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if "\u4e00" <= ch <= "\u9fff":
            j = i + 1
            while j < n and "\u4e00" <= raw[j] <= "\u9fff":
                j += 1
            chunk = raw[i:j]
            py = lazy_pinyin(chunk, style=Style.NORMAL)
            part = "_".join(x.lower() for x in py if x)
            if part:
                pieces.append(part)
            i = j
        else:
            j = i
            while j < n and not ("\u4e00" <= raw[j] <= "\u9fff"):
                j += 1
            chunk = raw[i:j]
            part = _snake_from_ascii_chunk(chunk)
            if part:
                pieces.append(part)
            i = j

    key = "_".join(pieces)
    key = re.sub(r"_+", "_", key).strip("_")
    if not key:
        key = "item"
    if target == "lifecycle_field_key":
        return _finalize_lifecycle_key(key)
    return _finalize_general_key(key)
