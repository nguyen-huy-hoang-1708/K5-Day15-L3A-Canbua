"""Dựng file số tổng hợp cho bản chạy thử từ data pre-class BTC cấp. Chỉ dùng thư viện chuẩn.

Chạy:  python data/build_aggregate.py data-btc/preclass
Ghi:   data/preclass_day_stats.json — CHỈ số tổng hợp theo ngày học và ý kiến thức (KC),
       không có mã học viên, mã dòng hay chữ học viên viết → được commit (xem data/DATA_CARD.md).

Cách đếm khớp evidence/count_preclass.py:
- active_total: số hv có ≥1 sự kiện actor=learner (436).
- active_day: số hv có ≥1 sự kiện actor=learner trên bài có lesson_id chứa dayNN.
- KC: answers.csv, lan_thu = 1, was_correct True/False; gom theo (ngày của lesson_id, kc_code).
- video: cặp (hv, video) có video_opened / có cả video_ended, theo ngày của lesson_id.
- chat: số lượt trong chat.csv có transcript DayNN/…
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data-btc", "preclass")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preclass_day_stats.json")


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def day_of(s):
    m = re.search(r"day(\d+)", s or "", re.I)
    return int(m.group(1)) if m else None


ev = read("events.csv")
an = read("answers.csv")
ch = read("chat.csv")

learner = [e for e in ev if e["actor"] == "learner"]
active_total = len({e["hv"] for e in learner})

active_day = defaultdict(set)
lessons = defaultdict(set)
video_open = defaultdict(set)
video_end = defaultdict(set)
for e in ev:
    d = day_of(e["lesson_id"])
    if not d:
        continue
    if e["actor"] == "learner":
        active_day[d].add(e["hv"])
        lessons[d].add(e["lesson_id"].split(":", 1)[-1])
    if e["type"] == "video_opened":
        video_open[d].add((e["hv"], e["video"]))
    elif e["type"] == "video_ended":
        video_end[d].add((e["hv"], e["video"]))

kc = defaultdict(lambda: {"people": set(), "n": 0, "correct": 0, "lesson": ""})
for a in an:
    if a["lan_thu"] != "1" or a["was_correct"] not in ("True", "False"):
        continue
    d = day_of(a["lesson_id"])
    if not d or not a["kc_code"]:
        continue
    k = kc[(d, a["kc_code"])]
    k["people"].add(a["hv"])
    k["n"] += 1
    k["correct"] += a["was_correct"] == "True"
    k["lesson"] = a["lesson_id"].split(":", 1)[-1]

chat_day = defaultdict(int)
for c in ch:
    d = day_of(c["transcript"])
    if d:
        chat_day[d] += 1

days = {}
for d in sorted(active_day):
    kcs = []
    for (dd, code), k in kc.items():
        if dd != d:
            continue
        kcs.append({"kc": code, "bai": k["lesson"], "so_nguoi": len(k["people"]),
                    "so_lan_tra_loi_dau": k["n"], "so_dung_lan_dau": k["correct"],
                    "ti_le_dung_pct": round(k["correct"] / k["n"] * 100, 1)})
    kcs.sort(key=lambda r: (r["ti_le_dung_pct"], -r["so_nguoi"]))
    opened = video_open[d]
    days[str(d)] = {
        "ngay": d,
        "bai": sorted(lessons[d]),
        "hoc_vien_co_hoat_dong": len(active_day[d]),
        "video_mo": len(opened),
        "video_xem_het": len(video_end[d] & opened),
        "luot_hoi_tro_giang_ai": chat_day.get(d, 0),
        "kc": kcs,
    }

out = {
    "nguon": "data/preclass BTC cấp (AI20K khoá 5), 05/11–25/11/2026, Day01–Day13",
    "tong_hoc_vien_co_hoat_dong": active_total,
    "ngay": days,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("Đã ghi %s · %d ngày · %d KC" % (OUT, len(days), sum(len(v["kc"]) for v in days.values())))
