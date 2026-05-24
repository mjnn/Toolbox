from typing import Any


def normalize_count_result(raw_total: Any) -> int:
    """统一处理 SQL count 查询的返回形态。"""
    if raw_total is None:
        return 0
    if isinstance(raw_total, int):
        return raw_total
    return int(raw_total[0])
