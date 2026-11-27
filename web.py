"""Giao diện web 1 màn hình cho Radar pre-class — chỉ dùng thư viện chuẩn Python.

Chạy:  python web.py            → mở http://localhost:8000
       python web.py 8080       → đổi cổng

Không thay luồng chính: mọi câu trả lời vẫn đi qua answer() trong codebase/agent.py
(cùng luật chặn, cùng bước kiểm số, cùng model trong .env) như `python run.py` và `python run.py eval`.
Trang chỉ thêm biểu đồ vẽ từ số tổng hợp (get_day_stats) — không gọi model thêm lần nào.

Cache theo ngày (chỉ ở giao diện web, KHÔNG ở answer() — để eval/simulate vẫn đo token thật):
- Radar của mỗi ngày lưu ở .cache/radar.json (đã có trong .gitignore). Bấm lại cùng ngày → trả bản đã lưu, 0 token.
- Tự bỏ cache khi data/preclass_day_stats.json đổi (so mtime) hoặc khi bấm "Hỏi lại AI" (?refresh=1).
- Chỉ lưu kết quả thành công (không lưu lỗi gọi model).
"""
import json
import os
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "codebase"))

import tracing  # noqa: E402
from agent import MIN_KC_PEOPLE, WEAK_PCT, _find_days, answer  # noqa: E402
from tools import get_day_stats, list_days  # noqa: E402

import game  # noqa: E402  (trò chơi Mê cung pre-class, /game)

GAME_PAGE = os.path.join(ROOT, "web", "game.html")
ANSWER_LOCK = threading.Lock()  # tracing dùng trạng thái chung → mỗi lúc chỉ chạy 1 answer()

PAGE = os.path.join(ROOT, "web", "index.html")
CACHE_FILE = os.path.join(ROOT, ".cache", "radar.json")
STATS_FILE = os.path.join(ROOT, "data", "preclass_day_stats.json")
VIDEO_FILE = os.path.join(ROOT, "data", "preclass_video_stats.json")


def videos_of_day(day):
    """Số tổng hợp video của một ngày (data/build_video_stats.py). Không gọi model."""
    try:
        with open(VIDEO_FILE, encoding="utf-8") as f:
            d = json.load(f)
    except OSError:
        return {"video": [], "error": "chưa có data/preclass_video_stats.json — chạy python data/build_video_stats.py"}
    vids = sorted((v for v in d["video"] if v["ngay"] == day), key=lambda v: -v["nguoi_xem"])
    return {"video": vids, "khoang_giay": d["khoang_giay"], "nguoi_xem_toi_thieu": d["nguoi_xem_toi_thieu"]}


def _stats_version():
    return int(os.path.getmtime(STATS_FILE))


def _cache_load():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            c = json.load(f)
        return c if c.get("version") == _stats_version() else {"version": _stats_version(), "days": {}}
    except (OSError, ValueError):
        return {"version": _stats_version(), "days": {}}


def _cache_save(c):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False)
    os.replace(tmp, CACHE_FILE)


def radar_day(day, refresh=False):
    c = _cache_load()
    hit = c["days"].get(str(day))
    if hit and not refresh:
        r = dict(hit["result"])
        r["cache"] = {"hit": True, "saved_at": hit["saved_at"]}
        return r
    r = run_answer("Day %d lớp đang hổng ý nào?" % day)
    if not r["error"]:
        c["days"][str(day)] = {"saved_at": time.strftime("%H:%M %d/%m/%Y"), "result": r}
        _cache_save(c)
    r["cache"] = {"hit": False}
    return r


def overview():
    """Tổng quan khoá: theo ngày — người có hoạt động / tổng, video xem hết / mở, số ý đang hổng. Không gọi model."""
    out = []
    for d in list_days():
        st = get_day_stats(d["ngay"])
        enough = [k for k in st["kc"] if k["so_nguoi"] >= MIN_KC_PEOPLE]
        out.append({"ngay": st["ngay"], "bai": st["bai"],
                    "hoc_vien": st["hoc_vien_co_hoat_dong"], "tong": st["tong_hoc_vien_co_hoat_dong"],
                    "video_mo": st["video_mo"], "video_xem_het": st["video_xem_het"],
                    "luot_hoi_ai": st["luot_hoi_tro_giang_ai"],
                    "so_y": len(st["kc"]), "so_y_du_nguoi": len(enough),
                    "so_y_hong": sum(k["ti_le_dung_pct"] < WEAK_PCT for k in enough),
                    "cached": str(st["ngay"]) in _cache_load()["days"]})
    return {"days": out, "min_people": MIN_KC_PEOPLE, "weak_pct": WEAK_PCT}


def run_answer(text):
    with ANSWER_LOCK:
        return _run_answer(text)


def _run_answer(text):
    tracing.begin("web")
    try:
        out = answer(text)["output"]
        err = ""
    except Exception as e:  # lỗi gọi model: báo trên trang, không làm sập server
        out, err = "", "%s: %s" % (type(e).__name__, e)
    s, _ = tracing.end()
    # chỉ kèm biểu đồ khi Radar thật sự trả số của một ngày (không kèm khi từ chối / hỏi lại)
    days = _find_days(text) if out.startswith("Radar pre-class Day") else []
    stats = get_day_stats(days[0]) if len(days) == 1 else {}
    return {"output": out, "error": err, "stats": stats,
            "meta": {"models": s["models"], "model_calls": s["model_calls"], "tool_calls": s["tool_calls"],
                     "tokens_in": s["tokens_in"], "tokens_out": s["tokens_out"]}}


class Handler(BaseHTTPRequestHandler):
    def _local(self):
        """Request từ chính máy chạy server (chỉ máy này được tạo tài khoản giảng viên)."""
        return self.client_address[0] in ("127.0.0.1", "::1")

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            with open(PAGE, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path in ("/game", "/game/"):
            with open(GAME_PAGE, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path.startswith("/game/api/"):
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            r = game.handle("GET", u.path, q, self.headers.get("X-Token"), self._local())
            return self._send(200 if r is not None else 404, r if r is not None else {"error": "không có"})
        if u.path == "/api/days":
            return self._send(200, {"days": list_days(), "min_people": MIN_KC_PEOPLE, "weak_pct": WEAK_PCT})
        if u.path == "/api/radar":
            day = (parse_qs(u.query).get("day") or [""])[0]
            if not day.isdigit():
                return self._send(400, {"error": "thiếu day"})
            refresh = (parse_qs(u.query).get("refresh") or ["0"])[0] == "1"
            return self._send(200, radar_day(int(day), refresh))
        if u.path == "/api/videos":
            day = (parse_qs(u.query).get("day") or [""])[0]
            return self._send(200, videos_of_day(int(day)) if day.isdigit() else {"video": []})
        if u.path == "/api/overview":
            return self._send(200, overview())
        return self._send(404, {"error": "không có trang này"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith("/game/api/"):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, {"error": "JSON không hợp lệ"})
            r = game.handle("POST", path, body if isinstance(body, dict) else {}, self.headers.get("X-Token"), self._local())
            return self._send(200 if r is not None else 404, r if r is not None else {"error": "không có"})
        if path != "/api/ask":
            return self._send(404, {"error": "không có trang này"})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            text = str(json.loads(self.rfile.read(n) or b"{}").get("text", ""))[:500]
        except ValueError:
            return self._send(400, {"error": "JSON không hợp lệ"})
        return self._send(200, run_answer(text))

    def log_message(self, fmt, *args):  # gọn log: bỏ các lượt hỏi trạng thái trò chơi (gọi liên tục)
        line = fmt % args
        if "/game/api/state" not in line and "/game/api/move" not in line:
            sys.stderr.write("%s\n" % line)


def main():
    for _stream in (sys.stdout, sys.stderr):  # Windows: console cp1258/cp1252 không in được tiếng Việt
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    port = int(args[0]) if args else 8000
    lan = "--lan" in sys.argv  # cho máy khác trong cùng mạng (lớp học) vào chơi
    host = "0.0.0.0" if lan else "127.0.0.1"
    print("Radar pre-class: http://localhost:%d  ·  Trò chơi: http://localhost:%d/game  (Ctrl+C để dừng)" % (port, port))
    if lan:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
        except OSError:
            ip = "<IP máy này>"
        print("Học viên cùng mạng vào: http://%s:%d/game" % (ip, port))
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
