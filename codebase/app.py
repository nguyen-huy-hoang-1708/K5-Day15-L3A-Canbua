"""Canbua — AI-Powered Learning Intervention Engine (Detect → Intervene → Evaluate).

Chạy bằng:
  python run.py           → mở Web App tối giản tại http://127.0.0.1:8765
  python run.py --cli     → chế độ dòng lệnh hỏi trực tiếp answer() trong agent.py
  python run.py eval      → vẫn gọi trực tiếp codebase/agent.py (không bị ảnh hưởng)
"""
import gzip
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

for _stream in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CODEBASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODEBASE_DIR)
WEB_DIR = os.path.join(CODEBASE_DIR, "web")
STATS_FILE = os.path.join(ROOT, "data", "preclass_day_stats.json")
sys.path.insert(0, CODEBASE_DIR)

import intervention_engine  # noqa: E402
import qr_svg  # noqa: E402
import rescue_store  # noqa: E402
import tracing  # noqa: E402
from agent import MIN_KC_PEOPLE, WEAK_PCT, answer  # noqa: E402
from ai import MODEL_NAME, MODEL_PROVIDER  # noqa: E402


_RADAR_CACHE = {"key": None, "data": None}
_HTML_CACHE = {"mtime": None, "text": ""}
_LAN_IP_CACHE = None


def _load_radar_data() -> dict:
    st_s = os.stat(STATS_FILE)
    kb_path = intervention_engine.KC_KB_PATH
    st_k = os.stat(kb_path) if os.path.exists(kb_path) else None
    key = (st_s.st_mtime_ns, st_s.st_size, st_k.st_mtime_ns if st_k else 0, st_k.st_size if st_k else 0)
    if _RADAR_CACHE["key"] == key and _RADAR_CACHE["data"] is not None:
        return _RADAR_CACHE["data"]

    with open(STATS_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    kb = intervention_engine._load_kb()

    total_active = raw["tong_hoc_vien_co_hoat_dong"]
    days_list = []
    for d_key in sorted(raw["ngay"].keys(), key=lambda x: int(x)):
        d = raw["ngay"][d_key]
        kcs = []
        eligible_cnt = 0
        weak_cnt = 0
        for k in d["kc"]:
            is_eligible = k["so_nguoi"] >= MIN_KC_PEOPLE
            is_weak = is_eligible and (k["ti_le_dung_pct"] < WEAK_PCT)
            if is_eligible:
                eligible_cnt += 1
            if is_weak:
                weak_cnt += 1
            kcs.append(dict(k, is_eligible=is_eligible, is_weak=is_weak, has_grounded_kb=(k["kc"] in kb)))

        days_list.append({
            "ngay": d["ngay"],
            "bai": d["bai"],
            "hoc_vien_co_hoat_dong": d["hoc_vien_co_hoat_dong"],
            "ti_le_tham_gia_pct": round(d["hoc_vien_co_hoat_dong"] / total_active * 100, 1),
            "video_mo": d["video_mo"],
            "video_xem_het": d["video_xem_het"],
            "luot_hoi_tro_giang_ai": d["luot_hoi_tro_giang_ai"],
            "eligible_kc_count": eligible_cnt,
            "weak_kc_count": weak_cnt,
            "g10_insufficient": eligible_cnt == 0,
            "kc": kcs,
        })

    result = {
        "nguon": raw["nguon"],
        "tong_hoc_vien_co_hoat_dong": total_active,
        "min_kc_people": MIN_KC_PEOPLE,
        "weak_pct_threshold": WEAK_PCT,
        "days": days_list,
    }
    _RADAR_CACHE["key"] = key
    _RADAR_CACHE["data"] = result
    return result


def _load_index_html() -> str:
    html_path = os.path.join(WEB_DIR, "index.html")
    mtime = os.stat(html_path).st_mtime_ns
    if _HTML_CACHE["mtime"] != mtime:
        with open(html_path, encoding="utf-8") as f:
            _HTML_CACHE["text"] = f.read()
        _HTML_CACHE["mtime"] = mtime
    return _HTML_CACHE["text"]


def _student_session_view(summary: dict) -> dict:
    iv = summary["intervention"]
    sc = iv["scenario"]
    tr = iv["transfer_scenario"]
    return {
        "session_code": summary["session_code"],
        "day": summary["day"],
        "kc_code": summary["kc_code"],
        "intervention": {
            "topic": iv["topic"],
            "learning_objective": iv["learning_objective"],
            "scenario": {k: v for k, v in sc.items() if k != "correct_index"},
            "transfer_scenario": {k: v for k, v in tr.items() if k != "correct_index"},
            "extra_questions": [
                {k: v for k, v in eq.items() if k != "correct_index"}
                for eq in (iv.get("extra_questions") or [])
            ],
        },
    }


def _find_kc_meta(day: int, kc_code: str) -> dict:
    for d in _load_radar_data()["days"]:
        if d["ngay"] == int(day):
            for k in d["kc"]:
                if k["kc"] == kc_code:
                    return k
    return {}


def _lan_ip() -> str:
    global _LAN_IP_CACHE
    if _LAN_IP_CACHE:
        return _LAN_IP_CACHE
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        _LAN_IP_CACHE = ip
        return ip
    except Exception:
        return "127.0.0.1"


def _status_payload() -> dict:
    port = int(os.environ.get("CANBUA_PORT", "8765"))
    lan_ip = _lan_ip()
    pub_url = get_public_url()
    return {
        "provider": MODEL_PROVIDER,
        "model": MODEL_NAME or "fake",
        "is_live_ai": MODEL_PROVIDER != "fake",
        "lan_ip": lan_ip,
        "lan_url": f"http://{lan_ip}:{port}",
        "public_url": pub_url,
        "tunnel_active": bool(pub_url),
        "port": port,
    }


_TUNNEL_LOCK = threading.Lock()
_TUNNEL_PROC = None
_PUBLIC_URL = os.environ.get("CANBUA_PUBLIC_URL", "").strip()
_TUNNEL_ERR = ""


def _drain_tunnel_stream(stream, url_box, ev):
    global _PUBLIC_URL
    try:
        for raw_line in iter(stream.readline, ""):
            m = re.search(r"https://[a-zA-Z0-9.-]+\.lhr\.life", raw_line)
            if m:
                new_url = m.group(0)
                if not url_box[0]:
                    url_box[0] = new_url
                    ev.set()
                else:
                    with _TUNNEL_LOCK:
                        _PUBLIC_URL = new_url
    except Exception:
        pass


def get_public_url() -> str:
    global _TUNNEL_PROC, _PUBLIC_URL
    with _TUNNEL_LOCK:
        if _TUNNEL_PROC is not None and _TUNNEL_PROC.poll() is not None:
            _TUNNEL_PROC = None
            _PUBLIC_URL = ""
        return _PUBLIC_URL


def stop_public_tunnel() -> dict:
    global _TUNNEL_PROC, _PUBLIC_URL, _TUNNEL_ERR
    with _TUNNEL_LOCK:
        proc = _TUNNEL_PROC
        _TUNNEL_PROC = None
        _PUBLIC_URL = ""
        _TUNNEL_ERR = ""
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    return {"tunnel_active": False, "public_url": ""}


def start_public_tunnel(port: int, timeout: float = 12.0) -> dict:
    global _TUNNEL_PROC, _PUBLIC_URL, _TUNNEL_ERR
    with _TUNNEL_LOCK:
        if _PUBLIC_URL and (_TUNNEL_PROC is None or _TUNNEL_PROC.poll() is None):
            return {"tunnel_active": True, "public_url": _PUBLIC_URL}
        if _TUNNEL_PROC and _TUNNEL_PROC.poll() is not None:
            _TUNNEL_PROC = None

        cmd = [
            "ssh", "-T",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=" + ("NUL" if os.name == "nt" else "/dev/null"),
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=2",
            "-o", "ExitOnForwardFailure=yes",
            "-R", f"80:127.0.0.1:{int(port)}",
            "nokey@localhost.run",
        ]
        kw = {}
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                **kw,
            )
        except FileNotFoundError:
            _TUNNEL_ERR = "Máy chưa cài lệnh `ssh` để tạo link public."
            raise RuntimeError(_TUNNEL_ERR)

        url_box = [""]
        ev = threading.Event()
        threading.Thread(target=_drain_tunnel_stream, args=(proc.stdout, url_box, ev), daemon=True).start()
        threading.Thread(target=_drain_tunnel_stream, args=(proc.stderr, url_box, ev), daemon=True).start()
        _TUNNEL_PROC = proc

    deadline = time.monotonic() + timeout
    while not ev.is_set() and time.monotonic() < deadline:
        if proc.poll() is not None:
            break
        ev.wait(0.2)

    with _TUNNEL_LOCK:
        if url_box[0]:
            _PUBLIC_URL = url_box[0]
            _TUNNEL_ERR = ""
            return {"tunnel_active": True, "public_url": _PUBLIC_URL}
        if proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        _TUNNEL_PROC = None
        _PUBLIC_URL = ""
        _TUNNEL_ERR = "Không lấy được link public từ localhost.run (kiểm tra kết nối Internet)."
        raise RuntimeError(_TUNNEL_ERR)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def setup(self):
        super().setup()
        try:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200, extra_headers: dict = None):
        accept_enc = self.headers.get("Accept-Encoding") or ""
        use_gzip = ("gzip" in accept_enc.lower()) and len(body) >= 512
        if use_gzip:
            body = gzip.compress(body, compresslevel=5)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status=status)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html", "/student"):
            html_text = _load_index_html()
            join_code = (qs.get("join") or [""])[0].strip().upper()
            is_student = bool(join_code or "student" in qs.get("mode", []) or path == "/student")
            boot_js = ""
            if is_student:
                if join_code:
                    summary = rescue_store.get_session_summary(join_code)
                    if summary:
                        boot_js = f"<script>window.__INIT_STUDENT__={json.dumps(_student_session_view(summary), ensure_ascii=False).replace('</', '<\\/')};</script>"
            else:
                teacher_boot = {
                    "radar": _load_radar_data(),
                    "status": _status_payload(),
                    "sessions": rescue_store.list_sessions(),
                }
                boot_js = f"<script>window.__INIT_TEACHER__={json.dumps(teacher_boot, ensure_ascii=False).replace('</', '<\\/')};</script>"
            if boot_js:
                html_text = html_text.replace("<script>", boot_js + "\n  <script>", 1)
            self._send_bytes(html_text.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/api/status":
            return self._send_json(_status_payload())

        if path == "/api/radar":
            return self._send_json(_load_radar_data())

        if path == "/api/qr":
            text = (qs.get("text") or [""])[0].strip()
            if not text:
                return self._send_json({"error": "Thiếu tham số text"}, 400)
            try:
                svg = qr_svg.render_qr_svg(text).encode("utf-8")
            except Exception as e:
                return self._send_json({"error": str(e)}, 400)
            self._send_bytes(svg, "image/svg+xml; charset=utf-8", extra_headers={"Cache-Control": "no-store"})
            return

        if path == "/api/sessions":
            return self._send_json({"sessions": rescue_store.list_sessions()})

        if path.startswith("/api/sessions/"):
            code = path.split("/api/sessions/")[1].strip("/")
            summary = rescue_store.get_session_summary(code)
            if not summary:
                return self._send_json({"error": "Không tìm thấy phiên " + code}, 404)
            if "student" in qs.get("view", []):
                return self._send_json(_student_session_view(summary))
            return self._send_json(summary)

        self._send_bytes(b"Not Found", "text/plain; charset=utf-8", status=404, extra_headers={"Connection": "close"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json()

            if path == "/api/radar/analyze":
                tracing.begin("web-radar")
                res = answer(body.get("query", ""))
                s, _ = tracing.end()
                return self._send_json({
                    "output": res.get("output", ""),
                    "models": s["models"],
                    "model_calls": s["model_calls"],
                    "tool_calls": s["tool_calls"],
                    "tokens_in": s["tokens_in"],
                    "tokens_out": s["tokens_out"],
                })

            if path == "/api/intervene/generate":
                day = int(body.get("day", 4))
                kc_code = (body.get("kc_code") or "").strip()
                use_ai = bool(body.get("use_ai", False))
                meta = _find_kc_meta(day, kc_code)
                tracing.begin("web-intervene")
                iv = intervention_engine.build_intervention(kc_code, meta, use_ai=use_ai)
                s, _ = tracing.end()
                return self._send_json({
                    "day": day,
                    "kc_code": kc_code,
                    "meta": meta,
                    "intervention": iv,
                    "tokens_in": s["tokens_in"],
                    "tokens_out": s["tokens_out"],
                })

            if path == "/api/intervene/save":
                kc_code = (body.get("kc_code") or "").strip()
                iv = body.get("intervention") or {}
                save_to_bank = bool(body.get("save_to_bank", False))
                chk = intervention_engine.validate_intervention(iv)
                if not chk["valid"]:
                    return self._send_json({"error": "Hoạt động chưa hợp lệ: " + "; ".join(chk["errors"])}, 400)
                if save_to_bank:
                    iv = intervention_engine.save_kc_to_kb(kc_code, iv)
                else:
                    iv = dict(iv)
                    iv["kc_code"] = kc_code
                    iv["generation_mode"] = "teacher_edited"
                    iv["validation"] = chk
                return self._send_json({"intervention": iv, "saved_to_bank": save_to_bank})

            if path == "/api/sessions":
                day = int(body.get("day", 4))
                kc_code = (body.get("kc_code") or "").strip()
                meta = _find_kc_meta(day, kc_code)
                iv = body.get("intervention") or intervention_engine.build_intervention(kc_code, meta)
                chk = intervention_engine.validate_intervention(iv)
                if not chk["valid"]:
                    return self._send_json({"error": "Hoạt động chưa hợp lệ: " + "; ".join(chk["errors"])}, 400)
                return self._send_json(rescue_store.create_session(day, kc_code, meta, iv), 201)

            if path.startswith("/api/sessions/") and path.endswith("/submit"):
                code = path.split("/")[3]
                return self._send_json(
                    rescue_store.submit_learning_activity(
                        code,
                        int(body["main_choice"]),
                        body.get("main_explanation", ""),
                        int(body["transfer_choice"]),
                        body.get("transfer_explanation", ""),
                        is_demo_simulated=False,
                        extra_choices=body.get("extra_choices"),
                        student_name=body.get("student_name", ""),
                    )
                )

            if path.startswith("/api/sessions/") and path.endswith("/simulate"):
                code = path.split("/")[3]
                return self._send_json(rescue_store.simulate_demo_responses(code, int(body.get("count", 10))))

            if path == "/api/tunnel/start":
                port = int(os.environ.get("CANBUA_PORT", "8765"))
                return self._send_json(start_public_tunnel(port))

            if path == "/api/tunnel/stop":
                return self._send_json(stop_public_tunnel())

            if path.startswith("/api/sessions/") and path.endswith("/clear-demo"):
                code = path.split("/")[3]
                return self._send_json(rescue_store.clear_demo_responses(code))

            return self._send_json({"error": "Không hỗ trợ endpoint này"}, 404)
        except Exception as e:
            return self._send_json({"error": str(e)}, 400)


def run_cli() -> int:
    print("Canbua CLI — gõ đầu vào rồi Enter. Thoát: Ctrl+C (hoặc Enter 2 lần dòng trống).")
    blank = 0
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            blank += 1
            if blank >= 2:
                return 0
            continue
        blank = 0
        tracing.begin("app")
        try:
            result = answer(text)
        except Exception as e:
            tracing.end()
            print("[lỗi] %s: %s" % (type(e).__name__, e))
            continue
        s, _ = tracing.end()
        print(result.get("output", "") if isinstance(result, dict) else result)
        print("   (model: %s · gọi model %d lần · công cụ %d lần · token vào %d / ra %d)"
              % (", ".join(s["models"]) or "—", s["model_calls"], s["tool_calls"], s["tokens_in"], s["tokens_out"]))


def main() -> int:
    if "--cli" in sys.argv:
        return run_cli()

    rescue_store.init_db()
    host = os.environ.get("CANBUA_HOST", "0.0.0.0")
    port = int(os.environ.get("CANBUA_PORT", "8765"))
    srv = ThreadingHTTPServer((host, port), Handler)
    local_url = f"http://127.0.0.1:{port}"
    lan_url = f"http://{_lan_ip()}:{port}"
    print("=" * 64)
    print("Canbua — AI-Powered Learning Intervention Engine")
    print(f"  Mở trên máy này : {local_url}")
    print(f"  Học viên cùng WiFi: {lan_url}")
    print(f"  AI Model        : {MODEL_PROVIDER} / {MODEL_NAME or 'fake'}")
    print("  Chế độ dòng lệnh: python run.py --cli · Dừng: Ctrl+C")
    if "--public" in sys.argv:
        try:
            t_res = start_public_tunnel(port)
            print(f"  Link Public (Internet): {t_res['public_url']}")
        except Exception as e:
            print(f"  Link Public (lỗi)     : {e}")
    print("=" * 64)
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(local_url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng Canbua server.")
        stop_public_tunnel()
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
