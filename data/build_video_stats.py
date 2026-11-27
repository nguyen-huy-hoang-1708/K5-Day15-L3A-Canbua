"""Dựng số tổng hợp "học viên bỏ ngang / tua qua ở đâu trong video" từ data pre-class BTC. Chỉ thư viện chuẩn.

Chạy:  python data/build_video_stats.py data-btc/preclass
Ghi:   data/preclass_video_stats.json — CHỈ số tổng hợp theo video và theo khoảng 15 giây, không có mã học viên.

Cách đếm (mỗi video):
- nguoi_xem: số học viên có ≥1 đoạn đã xem (video_segments_flushed.segments khác rỗng).
- giu_chan[i]: trong số người xem, bao nhiêu người đã xem ≥ 50% khoảng thứ i (15 giây) — gộp mọi đoạn đã xem của
  người đó qua mọi lần mở video.
- tua_qua[i]: bao nhiêu người xem có ≥1 lần tua tới (video_seeked, by = player, to − from ≥ 15 giây) nhảy qua trọn khoảng i.
- xem_het: số người xem có video_ended.
- cau_hoi: các giây có câu hỏi bật lên giữa video (quiz_item_opened.at_video_seconds, theo quiz_key = mã video).
- do_dai: độ dài video (giây) — lấy giá trị duration lớn nhất ghi được.
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data-btc", "preclass")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preclass_video_stats.json")
BIN = 15.0          # giây mỗi khoảng
MIN_SKIP = 15.0     # tua tới ít nhất bấy nhiêu giây mới tính là "tua qua"
MIN_VIEWERS = 10    # khớp MIN_KC_PEOPLE của Radar: dưới ngưỡng này không kết luận

with open(os.path.join(SRC, "events.csv"), encoding="utf-8-sig", newline="") as f:
    ev = list(csv.DictReader(f))

duration = defaultdict(float)
watched = defaultdict(lambda: defaultdict(list))   # video -> hv -> [(a, b)]
skips = defaultdict(lambda: defaultdict(list))     # video -> hv -> [(a, b)]
ended = defaultdict(set)
quiz = defaultdict(set)
lesson = {}

for e in ev:
    t, v = e["type"], e["video"]
    if t == "quiz_item_opened":
        d = json.loads(e["data"] or "{}")
        if d.get("quiz_key") and d.get("at_video_seconds") is not None:
            quiz[d["quiz_key"]].add(round(float(d["at_video_seconds"]), 1))
        continue
    if not v or e["actor"] != "learner":
        continue
    lesson.setdefault(v, e["lesson_id"].split(":", 1)[-1])
    if t == "video_segments_flushed":
        d = json.loads(e["data"] or "{}")
        duration[v] = max(duration[v], float(d.get("duration") or 0))
        for a, b in d.get("segments") or []:
            if b > a:
                watched[v][e["hv"]].append((float(a), float(b)))
    elif t == "video_seeked":
        d = json.loads(e["data"] or "{}")
        a, b = float(d.get("from") or 0), float(d.get("to") or 0)
        if d.get("by") == "player" and b - a >= MIN_SKIP:
            skips[v][e["hv"]].append((a, b))
    elif t == "video_ended":
        d = json.loads(e["data"] or "{}")
        duration[v] = max(duration[v], float(d.get("duration") or 0))
        ended[v].add(e["hv"])


def covered(intervals, lo, hi):
    """Số giây trong [lo, hi) được phủ bởi các đoạn (gộp đoạn chồng nhau)."""
    pts = sorted((max(a, lo), min(b, hi)) for a, b in intervals if b > lo and a < hi)
    tot, cur_a, cur_b = 0.0, None, None
    for a, b in pts:
        if cur_b is None or a > cur_b:
            if cur_b is not None:
                tot += cur_b - cur_a
            cur_a, cur_b = a, b
        else:
            cur_b = max(cur_b, b)
    if cur_b is not None:
        tot += cur_b - cur_a
    return tot


videos = []
for v, per_hv in watched.items():
    dur = duration[v]
    if dur <= 0:
        continue
    n_bins = max(1, int(-(-dur // BIN)))
    viewers = list(per_hv)
    keep, skip = [], []
    for i in range(n_bins):
        lo, hi = i * BIN, min(dur, (i + 1) * BIN)
        need = (hi - lo) * 0.5
        keep.append(sum(covered(per_hv[h], lo, hi) >= need for h in viewers))
        skip.append(sum(any(a <= lo and b >= hi for a, b in skips[v].get(h, [])) for h in viewers))
    m = re.match(r"d(\d+)", v)
    videos.append({
        "video": v, "ngay": int(m.group(1)) if m else None, "bai": lesson.get(v, ""),
        "do_dai": round(dur, 1), "khoang_giay": BIN, "nguoi_xem": len(viewers),
        "xem_het": len(ended[v] & set(viewers)), "giu_chan": keep, "tua_qua": skip,
        "cau_hoi": sorted(quiz.get(v, [])),
    })

videos.sort(key=lambda x: (x["ngay"] or 0, x["video"]))
out = {"nguon": "data/preclass BTC cấp (AI20K khoá 5) — events.csv: video_segments_flushed, video_seeked, video_ended, quiz_item_opened",
       "khoang_giay": BIN, "tua_toi_thieu_giay": MIN_SKIP, "nguoi_xem_toi_thieu": MIN_VIEWERS, "video": videos}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("Đã ghi %s · %d video · %d video có ≥ %d người xem"
      % (OUT, len(videos), sum(v["nguoi_xem"] >= MIN_VIEWERS for v in videos), MIN_VIEWERS))
