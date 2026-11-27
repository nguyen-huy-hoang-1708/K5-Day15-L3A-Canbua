"""Công cụ của bài toán Radar pre-class — khớp bảng "AI dựa vào đâu" ở spec.md §4.

Cả hai công cụ chỉ ĐỌC file số tổng hợp data/preclass_day_stats.json (dựng bằng data/build_aggregate.py).
Không công cụ nào trả mã học viên, không gửi tin, không sửa dữ liệu.
"""
import json
import os

from tracing import tool, TOOLS  # noqa: F401

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_FILE = os.path.join(ROOT, "data", "preclass_day_stats.json")
_CACHE = {}


def _load():
    if "d" not in _CACHE:
        with open(STATS_FILE, encoding="utf-8") as f:
            _CACHE["d"] = json.load(f)
    return _CACHE["d"]


@tool
def list_days() -> list:
    """list_days · Input: không có · Output: danh sách {"ngay", "bai", "hoc_vien_co_hoat_dong"} của mọi ngày có dữ liệu
    · Không tác động ra ngoài (chỉ đọc số tổng hợp)."""
    d = _load()
    return [{"ngay": v["ngay"], "bai": v["bai"], "hoc_vien_co_hoat_dong": v["hoc_vien_co_hoat_dong"]}
            for v in d["ngay"].values()]


@tool
def get_day_stats(day: int) -> dict:
    """get_day_stats · Input: day (int, số ngày học) · Output: số tổng hợp pre-class của ngày đó
    {"ngay", "bai", "hoc_vien_co_hoat_dong", "tong_hoc_vien_co_hoat_dong", "video_mo", "video_xem_het",
     "luot_hoi_tro_giang_ai", "kc": [{"kc", "bai", "so_nguoi", "so_lan_tra_loi_dau", "so_dung_lan_dau", "ti_le_dung_pct"}]}
    hoặc {} nếu ngày không có dữ liệu · Không tác động ra ngoài (chỉ đọc số tổng hợp, không có mã học viên)."""
    d = _load()
    v = d["ngay"].get(str(int(day)))
    if not v:
        return {}
    out = dict(v)
    out["tong_hoc_vien_co_hoat_dong"] = d["tong_hoc_vien_co_hoat_dong"]
    return out
