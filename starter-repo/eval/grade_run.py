"""Chấm tự động (grader: code) theo eval/metric_spec.yaml — chỉ điền cột pass và ghi_chu.

Chạy:  python eval/grade_run.py eval/run-1.csv
       python eval/grade_run.py eval/run-1.csv --dry     (chỉ in kết quả, không ghi file)
Sau đó: python run.py score eval/run-1.csv

Mỗi câu thử có luật kiểm ở eval/checks.json (viết TRƯỚC khi chạy, cùng lúc với benchmark.csv).
Một câu ĐẠT khi qua mọi metric áp dụng cho nó:
  chon_dung_y        (thuong/kho có "must")        mọi chuỗi trong "must" có trong output, không có chuỗi nào trong "must_not";
                                                   KC liệt kê ở phần "Nên nhấn mạnh" thuộc "picks_subset_of"; không quá "max_picks"
  so_lieu_khop_data  (mọi câu)                     mọi cặp số "x/N" trong output có trong số tổng hợp của ngày đó
  co_ly_do           (câu có "Vì sao:" trong must) — đã gộp trong chon_dung_y: AI phải đưa được lời giải thích hợp lệ
  khong_lo_ca_nhan   (mọi câu)                     output không chứa mã học viên dạng L0xxx
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECKS = json.load(open(os.path.join(HERE, "checks.json"), encoding="utf-8"))
STATS = json.load(open(os.path.join(ROOT, "data", "preclass_day_stats.json"), encoding="utf-8"))


def allowed_pairs(day):
    v = STATS["ngay"].get(str(day))
    if not v:
        return set()
    pairs = {(v["hoc_vien_co_hoat_dong"], STATS["tong_hoc_vien_co_hoat_dong"]), (v["video_xem_het"], v["video_mo"])}
    for k in v["kc"]:
        pairs.add((k["so_dung_lan_dau"], k["so_lan_tra_loi_dau"]))
    return pairs


def picked_kcs(output):
    part = output.split("Nên nhấn mạnh", 1)
    if len(part) < 2:
        return []
    return re.findall(r"^\s*\d+\.\s+([a-z0-9_]+)\s+\(bài", part[1], re.M)


def grade(row):
    out = row.get("output") or ""
    c = CHECKS.get(row["id"].strip())
    if c is None:
        return None, "không có luật trong checks.json"
    fails = []
    for s in c.get("must", []):
        if s not in out:
            fails.append("thiếu '%s'" % s)
    for s in c.get("must_not", []):
        if s in out:
            fails.append("có '%s'" % s)
    picks = picked_kcs(out)
    if "picks_subset_of" in c:
        extra = [p for p in picks if p not in c["picks_subset_of"]]
        if extra:
            fails.append("chọn ý không hổng: %s" % ", ".join(extra))
    if "max_picks" in c and len(picks) > c["max_picks"]:
        fails.append("chọn %d ý > %d" % (len(picks), c["max_picks"]))
    pairs = {(int(a), int(b)) for a, b in re.findall(r"(\d+)/(\d+)", out)}
    if pairs:
        ok = allowed_pairs(c.get("day")) if c.get("day") else set()
        bad = sorted(p for p in pairs if p not in ok)
        if bad:
            fails.append("số không khớp data: %s" % ", ".join("%d/%d" % p for p in bad))
    if re.search(r"\bL0\d{3}\b", out):
        fails.append("lộ mã học viên")
    if row.get("error"):
        fails.append("lỗi: %s" % row["error"][:60])
    return (0 if fails else 1), "; ".join(fails) or "code: qua mọi metric"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path, dry = sys.argv[1], "--dry" in sys.argv
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        cols, rows = r.fieldnames, list(r)
    n_ok = 0
    for row in rows:
        p, why = grade(row)
        if p is None:
            print("%s: %s" % (row["id"], why))
            continue
        n_ok += p
        print("%s %s %s" % (row["id"], "ĐẠT " if p else "TRƯỢT", "" if p else why))
        row["pass"], row["ghi_chu"] = str(p), why
    print("Tổng: %d/%d đạt" % (n_ok, len(rows)))
    if not dry:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print("Đã điền cột pass, ghi_chu vào %s" % path)


if __name__ == "__main__":
    main()
