"""Trò chơi "Mê cung pre-class" — logic phía server. Chỉ thư viện chuẩn. Được web.py gọi qua /game/api/*.

Luật:
- Mỗi học viên là một nhân vật trong mê cung, đi từ điểm xuất phát tới cổng đích ở giữa.
- Cửa "?" là chướng ngại: bước vào phải trả lời đúng 1 câu trắc nghiệm mới qua (cửa chỉ mở cho người đó).
  Sai / hết giờ → bị đứng yên PENALTY_WRONG giây, cửa vẫn đóng.
- Hộp may mắn: người đầu tiên bước vào nhận ngẫu nhiên Tăng tốc / Khiên (qua 1 cửa không cần trả lời) /
  Dịch chuyển (tới ô ngẫu nhiên) / Bẫy băng (đứng yên).
- Hai người gặp nhau (đi vào cùng một ô) → đấu tốc độ 1 câu: ai trả lời đúng trước thắng và đi tiếp,
  người thua bị loại. Trả lời sai thì mất lượt trong câu đó; cả hai sai / hết giờ → câu mới; 3 lần hoà → may rủi.
- Về đích: hạng 1, 2, 3… được cộng POINTS_BY_RANK vào hồ sơ (.game/profiles.json). Bị loại: 0 điểm.

Vai trò (không cần đăng nhập):
- Học viên chọn "Học viên" + nhập tên → vào phòng; điểm lưu theo tên (.game/profiles.json, không commit).
- Giảng viên chọn "Giảng viên" → bảng điều khiển; mặc định chỉ chọn được trên máy chạy server (TEACHER_LOCAL_ONLY).
- Chỉ giảng viên: bắt đầu / kết thúc / ván mới, xem toàn bộ mê cung, xem hồ sơ điểm.
- Học viên chỉ nhận vị trí hộp quà và người chơi khác trong tầm nhìn của mình (chống xem trộm qua API).

Câu hỏi: data/game_questions.json (bản nháp, chờ giảng viên duyệt). Đáp án không bao giờ gửi xuống trình duyệt;
thứ tự lựa chọn được xáo mỗi lần hỏi. Câu hỏi ưu tiên các ý kiến thức lớp đang hổng (số từ Radar).
"""
import json
import os
import random
import re
import secrets
import threading
import time
import uuid

ROOT = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(ROOT, "data", "game_questions.json")
STATS_FILE = os.path.join(ROOT, "data", "preclass_day_stats.json")
PROFILE_FILE = os.path.join(ROOT, ".game", "profiles.json")
SESSION_H = 12
VISION = 4.5                      # bán kính tầm nhìn (ô) — khớp sương mù ở web/game.html

CELLS_W, CELLS_H = 10, 7          # ô mê cung → lưới 21 x 15
N_GATES, N_BOXES = 14, 10
BRAID = 0.14                      # tỉ lệ phá thêm tường để có nhiều đường (may rủi khi chọn đường)
MOVE_MS, BOOST_MS = 150, 70
BOOST_S, PENALTY_WRONG, TRAP_S = 8, 3, 4
Q_TIME, DUEL_TIME = 30, 20
POINTS_BY_RANK = [100, 70, 50, 40, 30]
POINTS_MIN = 20
COLORS = ["#ff6b6b", "#4dabf7", "#51cf66", "#fcc419", "#cc5de8", "#ff922b", "#22b8cf", "#f06595",
          "#94d82d", "#845ef7", "#20c997", "#fab005"]
BOX_KINDS = [("boost", 3), ("shield", 3), ("teleport", 2), ("trap", 2)]
BOX_TEXT = {"boost": "⚡ Tăng tốc %d giây" % BOOST_S, "shield": "🛡 Khiên: qua 1 cửa không cần trả lời",
            "teleport": "🌀 Dịch chuyển tới ô ngẫu nhiên", "trap": "🧊 Bẫy băng: đứng yên %d giây" % TRAP_S}

LOCK = threading.RLock()


def _now():
    return time.time()


# ------------------------------------------------------------------ câu hỏi

def _load_questions():
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        qs = json.load(f)["cau_hoi"]
    weak = {}
    try:
        with open(STATS_FILE, encoding="utf-8") as f:
            for d in json.load(f)["ngay"].values():
                for k in d["kc"]:
                    if k["so_nguoi"] >= 10:
                        weak[k["kc"]] = k["ti_le_dung_pct"]
    except OSError:
        pass
    for q in qs:  # ý lớp càng hổng → càng hay được hỏi
        pct = weak.get(q["kc"])
        q["_w"] = 1.0 + (max(0.0, 100 - pct) / 20.0 if pct is not None else 0.5)
        q["_class_pct"] = pct
    return {q["id"]: q for q in qs}


QUESTIONS = _load_questions()


def _pick_question(exclude):
    pool = [q for q in QUESTIONS.values() if q["id"] not in exclude] or list(QUESTIONS.values())
    return random.choices(pool, weights=[q["_w"] for q in pool])[0]


def _present(qid):
    """Câu hỏi gửi xuống trình duyệt: lựa chọn đã xáo, KHÔNG có đáp án. Trả (dữ liệu gửi, chỉ số đúng sau xáo)."""
    q = QUESTIONS[qid]
    order = list(range(len(q["lua_chon"])))
    random.shuffle(order)
    return {"id": qid, "cau": q["cau"], "lua_chon": [q["lua_chon"][i] for i in order]}, order.index(q["dap_an"])


# ------------------------------------------------------------------ hồ sơ điểm

def _profiles():
    try:
        with open(PROFILE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_profiles(p):
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    tmp = PROFILE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PROFILE_FILE)


def _record(user, name, round_id, rank, points, result):
    p = _profiles()
    e = p.setdefault(user, {"tai_khoan": user, "ten": name, "diem": 0, "so_van": 0, "ve_nhat": 0, "lich_su": []})
    e["ten"] = name
    e["diem"] += points
    e["so_van"] += 1
    e["ve_nhat"] += 1 if rank == 1 else 0
    e["lich_su"].append({"van": round_id, "ket_qua": result, "hang": rank, "diem": points,
                         "luc": time.strftime("%H:%M %d/%m/%Y")})
    _save_profiles(p)


# ------------------------------------------------------------------ vai trò & phiên (không cần đăng nhập)

SESSIONS = {}      # token -> {"user", "role", "ten", "exp"}
TEACHER_LOCAL_ONLY = True   # True: chỉ máy chạy server được chọn vai trò Giảng viên (học viên trong mạng lớp không tự điều khiển ván)


def _slug(text):
    t = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    return re.sub(r"[^\w ]", "", t, flags=re.UNICODE)[:30]


def choose_role(role, ten, local):
    """Chọn vai trò thay cho đăng nhập. Học viên cần nhập tên (hồ sơ điểm theo tên); giảng viên chỉ bấm chọn."""
    if role not in ("hoc_vien", "giang_vien"):
        return {"error": "Chọn Giảng viên hoặc Học viên."}
    if role == "giang_vien":
        if TEACHER_LOCAL_ONLY and not local:
            return {"error": "Vai trò Giảng viên chỉ chọn được trên máy chạy trò chơi."}
        user, ten = "gv", "Giảng viên"
    else:
        ten = " ".join(str(ten or "").split())[:24]
        if not ten:
            return {"error": "Nhập tên của bạn."}
        user = "hv:" + _slug(ten)
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = {"sid": token, "user": user, "role": role, "ten": ten, "exp": _now() + SESSION_H * 3600}
    return {"token": token, "user": {"ten": ten, "role": role}}


def session(token):
    s = SESSIONS.get(token or "")
    if not s:
        return None
    if _now() > s["exp"]:
        SESSIONS.pop(token, None)
        return None
    return s


# ------------------------------------------------------------------ mê cung

def _gen_maze(seed):
    rnd = random.Random(seed)
    W, H = 2 * CELLS_W + 1, 2 * CELLS_H + 1
    t = [[1] * W for _ in range(H)]
    seen = {(0, 0)}
    stack = [(0, 0)]
    t[1][1] = 0
    while stack:
        cx, cy = stack[-1]
        nb = [(cx + dx, cy + dy, dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if 0 <= cx + dx < CELLS_W and 0 <= cy + dy < CELLS_H and (cx + dx, cy + dy) not in seen]
        if not nb:
            stack.pop()
            continue
        nx, ny, dx, dy = rnd.choice(nb)
        t[2 * cy + 1 + dy][2 * cx + 1 + dx] = 0
        t[2 * ny + 1][2 * nx + 1] = 0
        seen.add((nx, ny))
        stack.append((nx, ny))
    for y in range(1, H - 1):  # phá thêm tường → vòng lặp, nhiều lối
        for x in range(1, W - 1):
            if t[y][x] == 1 and ((x % 2 == 1 and y % 2 == 0) or (x % 2 == 0 and y % 2 == 1)) and rnd.random() < BRAID:
                t[y][x] = 0
    goal = (2 * (CELLS_W // 2) + 1, 2 * (CELLS_H // 2) + 1)
    spawns = [(1, 1), (W - 2, 1), (1, H - 2), (W - 2, H - 2), (W // 2 if (W // 2) % 2 else W // 2 - 1, 1),
              (W // 2 if (W // 2) % 2 else W // 2 - 1, H - 2), (1, H // 2 if (H // 2) % 2 else H // 2 - 1),
              (W - 2, H // 2 if (H // 2) % 2 else H // 2 - 1)]
    floor = [(x, y) for y in range(H) for x in range(W) if t[y][x] == 0]

    def near(p, qs, d):
        return any(abs(p[0] - q[0]) + abs(p[1] - q[1]) <= d for q in qs)

    def corridor(x, y):
        h = t[y][x - 1] == 0 and t[y][x + 1] == 0 and t[y - 1][x] == 1 and t[y + 1][x] == 1
        v = t[y - 1][x] == 0 and t[y + 1][x] == 0 and t[y][x - 1] == 1 and t[y][x + 1] == 1
        return h or v

    cand = [p for p in floor if corridor(*p) and not near(p, spawns + [goal], 2)]
    rnd.shuffle(cand)
    gates = []
    for p in cand:
        if len(gates) >= N_GATES:
            break
        if not near(p, gates, 2):
            gates.append(p)
    rest = [p for p in floor if p not in gates and not near(p, spawns + [goal], 2)]
    dead = [p for p in rest if sum(t[p[1] + dy][p[0] + dx] == 0 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) == 1]
    rnd.shuffle(dead)
    rnd.shuffle(rest)
    boxes = []
    for p in dead + rest:  # ưu tiên ngõ cụt: rẽ nhầm đường vẫn có thể gặp may
        if len(boxes) >= N_BOXES:
            break
        if not near(p, boxes + gates, 1):
            boxes.append(p)
    kinds = [k for k, n in BOX_KINDS for _ in range(n)]
    rnd.shuffle(kinds)
    return {"w": W, "h": H, "tiles": t, "goal": list(goal), "spawns": spawns, "gates": [list(g) for g in gates],
            "boxes": {"%d,%d" % p: kinds[i % len(kinds)] for i, p in enumerate(boxes)}}


# ------------------------------------------------------------------ trạng thái ván

class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.round_id = uuid.uuid4().hex[:6]
        self.maze = _gen_maze(random.randrange(10 ** 9))
        self.phase = "lobby"
        self.players = {}
        self.duels = {}
        self.feed = []
        self.qstats = {}
        self.started_at = None
        self.finish_order = []

    # ---- tiện ích
    def _log(self, text, kind="info"):
        self.feed.append({"t": _now(), "text": text, "kind": kind})
        self.feed = self.feed[-30:]

    def _stat(self, qid, ok):
        s = self.qstats.setdefault(qid, {"hoi": 0, "dung": 0})
        s["hoi"] += 1
        s["dung"] += 1 if ok else 0

    def _active(self, p):
        return p["status"] in ("playing", "question")

    # ---- vào phòng
    def join(self, sess, color=None):
        if not sess:
            return {"error": "Chọn vai trò Học viên và nhập tên trước."}
        if sess["role"] != "hoc_vien":
            return {"error": "Tài khoản giảng viên không vào chơi — dùng bảng điều khiển."}
        for p in self.players.values():
            if p["sid"] == sess["sid"]:
                return {"pid": p["pid"]}  # tải lại trang: vào lại đúng nhân vật
            if p["user"] == sess["user"]:
                return {"error": "Tên này đang có người dùng trong phòng — thêm họ hoặc chữ cái để phân biệt."}
        if self.phase != "lobby":
            return {"error": "Ván đang chạy — chờ ván sau nhé."}
        name = sess["ten"]
        pid = uuid.uuid4().hex[:10]
        used = {p["color"] for p in self.players.values()}
        color = color if color in COLORS and color not in used else next((c for c in COLORS if c not in used), COLORS[0])
        sp = self.maze["spawns"][len(self.players) % len(self.maze["spawns"])]
        self.players[pid] = {"pid": pid, "sid": sess["sid"], "user": sess["user"], "name": name, "color": color, "x": sp[0], "y": sp[1],
                             "status": "lobby", "opened": [], "asked": [], "shield": 0, "boost_until": 0,
                             "frozen_until": 0, "last_move": 0, "q": None, "rank": None, "points": 0,
                             "seen": _now(), "correct": 0, "wrong": 0}
        self._log("👋 %s vào phòng" % name)
        return {"pid": pid}

    def start(self):
        if self.phase != "lobby":
            return {"error": "Ván đã bắt đầu."}
        if not self.players:
            return {"error": "Chưa có ai vào phòng."}
        self.phase, self.started_at = "playing", _now()
        for p in self.players.values():
            p["status"] = "playing"
        self._log("🚩 Bắt đầu! Tìm đường tới cổng đích ở giữa mê cung.", "big")
        return {"ok": True}

    def end(self):
        if self.phase == "playing":
            for p in self.players.values():
                if p["status"] in ("playing", "question", "duel"):
                    _record(p["user"], p["name"], self.round_id, None, 0, "chưa về đích")
            self.phase = "ended"
            self._log("🏁 Giảng viên kết thúc ván.", "big")
        return {"ok": True}

    # ---- vòng thời gian (gọi mỗi lần có request)
    def tick(self):
        now = _now()
        if self.phase == "lobby":
            for pid in [k for k, p in self.players.items() if now - p["seen"] > 30]:
                self._log("%s rời phòng" % self.players[pid]["name"])
                del self.players[pid]
            return
        if self.phase != "playing":
            return
        for p in self.players.values():
            q = p["q"]
            if p["status"] == "question" and q and now > q["deadline"]:
                self._gate_fail(p, "⏱ %s hết giờ ở cửa câu hỏi" % p["name"])
        for d in list(self.duels.values()):
            if now > d["deadline"]:
                d["draws"] += 1
                if d["draws"] >= 3:
                    w = random.choice([d["a"], d["b"]])
                    self._finish_duel(d, w, "🎲 Hoà 3 lần — may rủi chọn %s" % self.players[w]["name"])
                else:
                    self._log("⏱ Hết giờ đấu — câu mới!")
                    self._new_duel_question(d)
        alive = [p for p in self.players.values() if p["status"] in ("playing", "question", "duel")]
        if not alive:
            self.phase = "ended"
            self._log("🏁 Ván kết thúc!", "big")

    # ---- di chuyển
    def move(self, pid, dx, dy):
        p = self.players.get(pid)
        if not p or self.phase != "playing" or p["status"] != "playing":
            return {"ok": False}
        now = _now()
        if now < p["frozen_until"]:
            return {"ok": False, "why": "frozen"}
        gap = (BOOST_MS if now < p["boost_until"] else MOVE_MS) / 1000.0
        if now - p["last_move"] < gap:
            return {"ok": False}
        nx, ny = p["x"] + dx, p["y"] + dy
        if not (0 <= nx < self.maze["w"] and 0 <= ny < self.maze["h"]) or self.maze["tiles"][ny][nx] == 1:
            return {"ok": False}
        p["last_move"] = now
        if [nx, ny] in self.maze["gates"]:
            if [nx, ny] not in p["opened"]:
                if p["shield"] > 0:
                    p["shield"] -= 1
                    p["opened"].append([nx, ny])
                    self._log("🛡 %s dùng khiên phá cửa" % p["name"])
                else:
                    item, right = _present(_pick_question(p["asked"])["id"])
                    p["asked"].append(item["id"])
                    p["q"] = {"kind": "gate", "item": item, "right": right, "gate": [nx, ny], "deadline": now + Q_TIME}
                    p["status"] = "question"
                    return {"ok": True, "question": True}
        p["x"], p["y"] = nx, ny
        self._after_step(p)
        return {"ok": True}

    def _after_step(self, p):
        now = _now()
        key = "%d,%d" % (p["x"], p["y"])
        kind = self.maze["boxes"].pop(key, None)
        if kind:
            self._log("🎁 %s mở hộp may mắn: %s" % (p["name"], BOX_TEXT[kind]), "luck")
            if kind == "boost":
                p["boost_until"] = now + BOOST_S
            elif kind == "shield":
                p["shield"] += 1
            elif kind == "trap":
                p["frozen_until"] = now + TRAP_S
            elif kind == "teleport":
                floor = [(x, y) for y in range(self.maze["h"]) for x in range(self.maze["w"])
                         if self.maze["tiles"][y][x] == 0 and [x, y] not in self.maze["gates"]
                         and [x, y] != self.maze["goal"]]
                p["x"], p["y"] = random.choice(floor)
        if [p["x"], p["y"]] == list(self.maze["goal"]):
            self._arrive(p)
            return
        for o in self.players.values():  # gặp người khác → đấu
            if o is not p and o["status"] == "playing" and (o["x"], o["y"]) == (p["x"], p["y"]):
                self._start_duel(p, o)
                break

    def _arrive(self, p):
        self.finish_order.append(p["pid"])
        rank = len(self.finish_order)
        pts = POINTS_BY_RANK[rank - 1] if rank <= len(POINTS_BY_RANK) else POINTS_MIN
        p.update(status="finished", rank=rank, points=pts)
        _record(p["user"], p["name"], self.round_id, rank, pts, "về đích")
        self._log("🏆 %s về đích hạng %d (+%d điểm)" % (p["name"], rank, pts), "big")

    # ---- câu hỏi ở cửa
    def answer(self, pid, qid, choice):
        p = self.players.get(pid)
        if not p or self.phase != "playing":
            return {"ok": False}
        if p["status"] == "duel":
            return self._duel_answer(p, qid, choice)
        q = p["q"]
        if p["status"] != "question" or not q or q["item"]["id"] != qid:
            return {"ok": False}
        ok = int(choice) == q["right"]
        self._stat(qid, ok)
        expl = QUESTIONS[qid]["giai_thich"]
        if ok:
            p["correct"] += 1
            p["opened"].append(q["gate"])
            p["x"], p["y"] = q["gate"]
            p["q"], p["status"] = None, "playing"
            self._log("✅ %s mở cửa" % p["name"])
            self._after_step(p)
            return {"ok": True, "correct": True, "giai_thich": expl}
        p["wrong"] += 1
        self._gate_fail(p, "❌ %s trả lời sai, bị giữ %d giây" % (p["name"], PENALTY_WRONG))
        return {"ok": True, "correct": False, "giai_thich": expl,
                "dap_an": q["item"]["lua_chon"][q["right"]]}

    def _gate_fail(self, p, text):
        p["q"], p["status"] = None, "playing"
        p["frozen_until"] = _now() + PENALTY_WRONG
        self._log(text, "bad")

    # ---- đấu tay đôi
    def _start_duel(self, a, b):
        did = uuid.uuid4().hex[:8]
        d = {"id": did, "a": a["pid"], "b": b["pid"], "draws": 0, "asked": list(set(a["asked"] + b["asked"]))}
        self.duels[did] = d
        for p in (a, b):
            p["status"], p["q"] = "duel", {"kind": "duel", "duel": did}
        self._log("⚔️ %s gặp %s — đấu tốc độ!" % (a["name"], b["name"]), "duel")
        self._new_duel_question(d)

    def _new_duel_question(self, d):
        q = _pick_question(d["asked"])
        d["asked"].append(q["id"])
        item, right = _present(q["id"])
        d.update(item=item, right=right, wrong=[], deadline=_now() + DUEL_TIME, started=_now())

    def _duel_answer(self, p, qid, choice):
        d = self.duels.get(p["q"]["duel"]) if p["q"] else None
        if not d or d["item"]["id"] != qid or p["pid"] in d["wrong"]:
            return {"ok": False}
        ok = int(choice) == d["right"]
        self._stat(qid, ok)
        if ok:
            p["correct"] += 1
            secs = _now() - d["started"]
            self._finish_duel(d, p["pid"], "⚡ %s trả lời đúng trước (%.1f giây)" % (p["name"], secs))
            return {"ok": True, "correct": True, "won": True}
        p["wrong"] += 1
        d["wrong"].append(p["pid"])
        if len(d["wrong"]) == 2:
            d["draws"] += 1
            if d["draws"] >= 3:
                w = random.choice([d["a"], d["b"]])
                self._finish_duel(d, w, "🎲 Cả hai sai 3 lần — may rủi chọn %s" % self.players[w]["name"])
            else:
                self._log("🤝 Cả hai trả lời sai — câu mới!")
                self._new_duel_question(d)
        return {"ok": True, "correct": False}

    def _finish_duel(self, d, winner, why):
        loser = d["b"] if winner == d["a"] else d["a"]
        w, l = self.players[winner], self.players[loser]
        w["status"], w["q"] = "playing", None
        w["last_move"] = _now()
        l.update(status="out", q=None)
        _record(l["user"], l["name"], self.round_id, None, 0, "bị loại khi đấu")
        self.duels.pop(d["id"], None)
        self._log("%s · %s bị loại, %s đi tiếp" % (why, l["name"], w["name"]), "duel")

    # ---- dữ liệu gửi trình duyệt
    def maze_view(self):
        m = self.maze
        return {"round": self.round_id, "w": m["w"], "h": m["h"], "tiles": m["tiles"], "goal": m["goal"],
                "gates": m["gates"]}

    def _sees(self, me, host, x, y):
        """Giảng viên thấy hết; học viên đang chơi chỉ thấy trong bán kính VISION; còn lại (đã xong / bị loại) thấy hết."""
        if host or self.phase != "playing":
            return True
        if not me or me["status"] not in ("playing", "question", "duel"):
            return bool(me)
        return ((x - me["x"]) ** 2 + (y - me["y"]) ** 2) ** .5 <= VISION + 0.6

    def _pview(self, p, me, host, now):
        v = {"pid": p["pid"], "name": p["name"], "color": p["color"], "x": p["x"], "y": p["y"],
             "status": p["status"], "rank": p["rank"], "points": p["points"],
             "frozen": max(0.0, p["frozen_until"] - now), "boost": max(0.0, p["boost_until"] - now),
             "shield": p["shield"], "opened": len(p["opened"])}
        if not (me and p["pid"] == me["pid"]) and not self._sees(me, host, p["x"], p["y"]):
            v["x"] = v["y"] = None
        return v

    def state(self, pid=None, host=False):
        now = _now()
        me = self.players.get(pid) if pid else None
        if me:
            me["seen"] = now
        out = {"round": self.round_id, "phase": self.phase, "now": now,
               "elapsed": (now - self.started_at) if self.started_at else 0,
               "players": [self._pview(p, me, host, now) for p in self.players.values()],
               "boxes": [b for b in ([int(v) for v in k.split(",")] for k in self.maze["boxes"]) if self._sees(me, host, b[0], b[1])],
               "feed": self.feed[-12:]}
        if me:
            m = {"pid": me["pid"], "opened": me["opened"], "status": me["status"], "shield": me["shield"],
                 "frozen": max(0.0, me["frozen_until"] - now), "boost": max(0.0, me["boost_until"] - now)}
            if me["status"] == "question" and me["q"]:
                m["question"] = dict(me["q"]["item"], left=max(0.0, me["q"]["deadline"] - now), total=Q_TIME)
            if me["status"] == "duel" and me["q"]:
                d = self.duels.get(me["q"]["duel"])
                if d:
                    opp = self.players[d["b"] if d["a"] == me["pid"] else d["a"]]
                    m["duel"] = dict(d["item"], left=max(0.0, d["deadline"] - now), total=DUEL_TIME,
                                     opponent={"name": opp["name"], "color": opp["color"]},
                                     locked=me["pid"] in d["wrong"], draws=d["draws"])
            out["me"] = m
        if host:
            out["qstats"] = sorted(
                [{"id": k, "cau": QUESTIONS[k]["cau"], "kc": QUESTIONS[k]["kc"], "hoi": v["hoi"], "dung": v["dung"],
                  "lop_pct": QUESTIONS[k]["_class_pct"]} for k, v in self.qstats.items()],
                key=lambda r: r["dung"] / max(1, r["hoi"]))
        return out


GAME = Game()


def profiles_view():
    p = _profiles()
    return sorted(p.values(), key=lambda e: (-e["diem"], e["ten"].lower()))


def handle(method, path, body, token=None, local=False):
    """Định tuyến /game/api/*. token: phiên đăng nhập (header X-Token); local: request từ chính máy chạy server."""
    with LOCK:
        GAME.tick()
        sess = session(token)
        teacher = bool(sess and sess["role"] == "giang_vien")
        # ---- tài khoản
        if method == "GET" and path == "/game/api/auth/me":
            return {"user": {"ten": sess["ten"], "role": sess["role"]} if sess else None,
                    "can_teach": local or not TEACHER_LOCAL_ONLY}
        if method == "POST" and path == "/game/api/auth/role":
            return choose_role(body.get("role"), body.get("ten"), local)
        if method == "POST" and path == "/game/api/auth/logout":
            SESSIONS.pop(token or "", None)
            return {"ok": True}
        # ---- người chơi: pid phải thuộc tài khoản đang đăng nhập
        pid = body.get("pid")
        owner = GAME.players.get(pid, {}).get("sid") if pid else None
        if pid and (not sess or owner != sess["sid"]):
            pid = None
        if method == "GET" and path == "/game/api/maze":
            return GAME.maze_view()
        if method == "GET" and path == "/game/api/state":
            return GAME.state(pid, host=teacher and body.get("host") == "1")
        if method == "POST" and path == "/game/api/join":
            return GAME.join(sess, body.get("color"))
        if method == "POST" and path == "/game/api/move":
            dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.get(body.get("dir"), (0, 0))
            return GAME.move(pid, dx, dy) if (pid and (dx or dy)) else {"ok": False}
        if method == "POST" and path == "/game/api/answer":
            return GAME.answer(pid, body.get("qid"), body.get("choice", -1)) if pid else {"ok": False}
        # ---- chỉ giảng viên
        if path in ("/game/api/profiles", "/game/api/host/start", "/game/api/host/end", "/game/api/host/new") and not teacher:
            return {"error": "Chỉ giảng viên làm được việc này."}
        if method == "GET" and path == "/game/api/profiles":
            return {"profiles": profiles_view(), "da_duyet_cau_hoi": False}
        if method == "POST" and path == "/game/api/host/start":
            return GAME.start()
        if method == "POST" and path == "/game/api/host/end":
            return GAME.end()
        if method == "POST" and path == "/game/api/host/new":
            GAME.reset()
            return {"ok": True}
    return None
