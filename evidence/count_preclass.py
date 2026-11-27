"""Đếm bằng chứng từ data pre-class BTC cấp. Chỉ dùng thư viện chuẩn.

Chạy:  python evidence/count_preclass.py data-btc/preclass
In ra các số dùng trong evidence/data-mining.md và spec.md §1–§2.
Không ghi file, không in mã học viên (luật dùng data: không xếp hạng, không đoán ai là ai).
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "data-btc/preclass")


def read(name):
    with open(DATA / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def pct(x, n):
    return f"{x}/{n} ({x / n * 100:.1f}%)" if n else f"{x}/0"


def day_of(lesson_id):
    m = re.search(r"day(\d+)", lesson_id or "")
    return int(m.group(1)) if m else None


ev = read("events.csv")
an = read("answers.csv")
ch = read("chat.csv")

learner_ev = [e for e in ev if e["actor"] == "learner"]
active = {e["hv"] for e in learner_ev}
N = len(active)
print(f"[1] Học viên có hoạt động (actor=learner, ≥1 sự kiện): {N}")

# [2] Số học viên có hoạt động trên bài của từng ngày học
by_day = defaultdict(set)
for e in learner_ev:
    d = day_of(e["lesson_id"])
    if d:
        by_day[d].add(e["hv"])
print("[2] Học viên có ≥1 sự kiện trên bài DayNN / học viên có hoạt động:")
for d in sorted(by_day):
    print(f"    Day{d:02d}: {pct(len(by_day[d]), N)}")

# [3] Xem hết video: cặp (học viên, video) có video_ended / cặp có video_opened
opened = {(e["hv"], e["video"]) for e in ev if e["type"] == "video_opened"}
ended = {(e["hv"], e["video"]) for e in ev if e["type"] == "video_ended"}
print(f"[3] Cặp (học viên, video) xem tới cuối / đã mở: {pct(len(ended & opened), len(opened))}")

# [4] Đúng ở lần trả lời đầu theo ý kiến thức (KC), chỉ câu chấm đúng/sai, KC có ≥20 người
first = [a for a in an if a["lan_thu"] == "1" and a["was_correct"] in ("True", "False")]
ok = sum(a["was_correct"] == "True" for a in first)
print(f"[4] Lần đầu trả lời đúng (mọi KC): {pct(ok, len(first))}")
kc = defaultdict(list)
for a in first:
    kc[a["kc_code"]].append(a)
rows = []
for k, v in kc.items():
    people = {a["hv"] for a in v}
    if len(people) >= 20:
        rows.append((sum(a["was_correct"] == "True" for a in v) / len(v), k, len(v), len(people),
                     sum(a["was_correct"] == "True" for a in v)))
rows.sort()
print(f"    KC có ≥20 người trả lời: {len(rows)}; KC đúng < 75%: {sum(r[0] < 0.75 for r in rows)}")
for acc, k, n, p, x in rows[:8]:
    print(f"    {k}: đúng {pct(x, n)} · {p} người")

# [5] Dùng trợ giảng AI
chat_users = {c["hv"] for c in ch}
print(f"[5] Học viên từng nhắn AI / có hoạt động: {pct(len(chat_users), N)} · {len(ch)} lượt chat")

# [6] Mini lab: số lần bấm bỏ qua trên số lần lab_completed
labs = [json.loads(e["data"] or "{}") for e in ev if e["type"] == "lab_completed"]
skipped = sum(d.get("skipped") is True for d in labs)
print(f"[6] lab_opened: {sum(e['type'] == 'lab_opened' for e in ev)} · lab_completed bấm bỏ qua: {pct(skipped, len(labs))}")

# [7] Ví dụ dòng: 5 lần trả lời sai lần đầu ở KC đúng thấp nhất (chỉ in mã dòng A…, không in hv)
worst = rows[0][1] if rows else None
ex = [a["id"] for a in first if a["kc_code"] == worst and a["was_correct"] == "False"][:5]
print(f"[7] Ví dụ answers.csv id sai lần đầu ở KC {worst}: {', '.join(ex)}")
