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
import collections
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
KC_KB_FILE = os.path.join(ROOT, "data", "kc_knowledge.json")
STATS_FILE = os.path.join(ROOT, "data", "preclass_day_stats.json")
PROFILE_FILE = os.path.join(ROOT, ".game", "profiles.json")
FOCUS_INFO = {"day": None, "kc_code": None, "topic": None, "approved": False, "custom_count": 0}
HOST_KEYS = set()


def issue_host_key() -> str:
    k = secrets.token_urlsafe(16)
    with LOCK:
        HOST_KEYS.add(k)
        if len(HOST_KEYS) > 20:
            HOST_KEYS.pop()
    return k


def is_valid_host_key(key) -> bool:
    return bool(key) and key in HOST_KEYS
SESSION_H = 12
VISION = 2.7                      # bán kính tầm nhìn hẹp (ô) — khớp sương mù tối ở web/game.html

CELLS_W, CELLS_H = 12, 8          # mê cung rộng & khó hơn → lưới 25 x 17
N_GATES, N_BOXES = 16, 11
BRAID = 0.09                      # ít lối tắt hơn → nhiều ngõ cụt & phân nhánh khó hơn
MOVE_MS, BOOST_MS = 150, 70
BOOST_S, PENALTY_WRONG, TRAP_S = 8, 4, 4
Q_TIME, DUEL_TIME = 25, 18
POINTS_BY_RANK = [100, 70, 50, 40, 30]
POINTS_MIN = 20
COLORS = ["#ff6b6b", "#4dabf7", "#51cf66", "#fcc419", "#cc5de8", "#ff922b", "#22b8cf", "#f06595",
          "#94d82d", "#845ef7", "#20c997", "#fab005"]
BOX_KINDS = [("boost", 3), ("shield", 3), ("teleport", 2), ("trap", 2)]
BOX_TEXT = {"boost": "⚡ Tăng tốc %d giây" % BOOST_S, "shield": "🛡 Khiên — qua 1 cửa không cần trả lời",
            "teleport": "🌀 Dịch chuyển tới ô ngẫu nhiên", "trap": "🧊 Bẫy băng — đứng yên %d giây" % TRAP_S}

LOCK = threading.RLock()


def _now():
    return time.time()


# ------------------------------------------------------------------ câu hỏi

def _load_questions():
    qs = []
    try:
        with open(QUESTIONS_FILE, encoding="utf-8") as f:
            qs = list(json.load(f).get("cau_hoi") or [])
    except OSError:
        qs = []
    seen_kcs = {q.get("kc") for q in qs}
    # Bổ sung thêm câu hỏi từ kho chuẩn 160 KC (data/kc_knowledge.json) cho các KC chưa có trong game_questions.json
    if os.path.exists(KC_KB_FILE):
        try:
            with open(KC_KB_FILE, encoding="utf-8") as f:
                kb = json.load(f)
            for kc_code, item in kb.items():
                if kc_code in seen_kcs:
                    continue
                sc = item.get("scenario") or {}
                opts = sc.get("options") or []
                ci = sc.get("correct_index")
                if sc.get("question") and isinstance(opts, list) and len(opts) >= 2 and isinstance(ci, int) and 0 <= ci < len(opts):
                    ctx = (sc.get("context") or "").strip()
                    prompt_txt = f"{ctx}\n\n{sc['question']}" if ctx and len(ctx) <= 260 else sc["question"]
                    qs.append({
                        "id": f"kb_{kc_code}",
                        "kc": kc_code,
                        "cau": prompt_txt,
                        "lua_chon": list(opts),
                        "dap_an": ci,
                        "giai_thich": (item.get("feedback") or {}).get("relearn", ""),
                    })
                    seen_kcs.add(kc_code)
        except (OSError, ValueError):
            pass

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


def _clean_misconception(text: str) -> str:
    txt = re.sub(r"^Giả thuyết\s*\d*\s*\([^)]*\)\s*:\s*", "", (text or "").strip(), flags=re.I)
    return txt.strip()


def _build_kc_support_questions(kc_code: str, intervention: dict) -> list:
    """Rút thêm 2–3 câu trắc nghiệm nhanh từ chính 9 phần kiến thức của KC đang xử lý (không lấy KC khác)."""
    out = []
    topic = (intervention.get("topic") or kc_code).strip()
    fb = intervention.get("feedback") or {}
    relearn = (fb.get("relearn") or "").strip()
    when_apply = (fb.get("when_to_apply") or "").strip()
    why_wrong = (fb.get("why_wrong") or "").strip()
    mis = [_clean_misconception(m) for m in (intervention.get("possible_misconceptions") or []) if m]
    comps = [c.strip() for c in (intervention.get("comparison_approaches") or []) if c]

    # Câu bổ trợ 1: Nguyên tắc áp dụng đúng của KC
    if relearn and mis:
        distractors = [m for m in mis[:2] if m != relearn]
        distractors.append("Áp dụng cố định cho mọi bài toán mà không cần xem xét điều kiện hay chi phí.")
        opts = [relearn] + distractors[:3]
        out.append({
            "id": f"iv_{kc_code}_principle",
            "kc": kc_code,
            "cau": f"[{topic}] Nguyên tắc cốt lõi nào sau đây là ĐÚNG?",
            "lua_chon": opts,
            "dap_an": 0,
            "giai_thich": why_wrong or relearn,
        })

    # Câu bổ trợ 2: So sánh 2 cách triển khai của KC
    if len(comps) >= 2:
        wrong_way, right_way = comps[0], comps[1]
        if "đúng" in wrong_way.lower() and "sai" in right_way.lower():
            wrong_way, right_way = right_way, wrong_way
        out.append({
            "id": f"iv_{kc_code}_compare",
            "kc": kc_code,
            "cau": f"[{topic}] So sánh cách triển khai dưới đây, cách nào ĐÚNG bản chất?",
            "lua_chon": [
                right_way,
                wrong_way,
                "Cả hai cách đều cho kết quả và chi phí giống hệt nhau.",
            ],
            "dap_an": 0,
            "giai_thich": relearn or why_wrong,
        })

    # Câu bổ trợ 3: Khi nào nên áp dụng KC này
    if when_apply:
        opts = [
            when_apply,
            mis[0] if mis else "Chỉ cần làm theo thói quen, không cần kiểm tra bối cảnh bài toán.",
            "Không bao giờ cần quan tâm đến điều kiện biên của bài toán.",
        ]
        out.append({
            "id": f"iv_{kc_code}_when",
            "kc": kc_code,
            "cau": f"[{topic}] Khi nào nên áp dụng kiến thức này trong thực tế?",
            "lua_chon": opts,
            "dap_an": 0,
            "giai_thich": when_apply,
        })
    return out


def suggest_support_questions(kc_code: str, intervention: dict) -> list:
    """Sinh gợi ý 2–4 câu trắc nghiệm nhanh của ĐÚNG KC đó để giảng viên XEM, SỬA và TỰ DUYỆT ở Bước 2."""
    suggestions = []
    try:
        with open(QUESTIONS_FILE, encoding="utf-8") as f:
            for q in json.load(f).get("cau_hoi") or []:
                if q.get("kc") == kc_code:
                    suggestions.append({
                        "context": "",
                        "question": q["cau"],
                        "options": list(q["lua_chon"]),
                        "correct_index": int(q["dap_an"]),
                    })
    except OSError:
        pass
    for sq in _build_kc_support_questions(kc_code, intervention):
        suggestions.append({
            "context": "",
            "question": sq["cau"],
            "options": list(sq["lua_chon"]),
            "correct_index": int(sq["dap_an"]),
        })
    return suggestions


def set_approved_intervention(day, kc_code, intervention):
    """CHỈ nạp đúng các câu hỏi giảng viên đã xem và bấm Duyệt ở Bước 2 (tuyệt đối không tự chèn câu chưa duyệt)."""
    global QUESTIONS
    with LOCK:
        focused = {}
        fb = intervention.get("feedback") or {}
        explain = fb.get("relearn") or fb.get("why_wrong") or ""
        class_pct = None
        try:
            with open(STATS_FILE, encoding="utf-8") as f:
                for d in json.load(f)["ngay"].values():
                    for k in d["kc"]:
                        if k["kc"] == kc_code:
                            class_pct = k.get("ti_le_dung_pct")
        except OSError:
            pass

        def _add(qid, block, weight):
            opts = block.get("options") or []
            ci = block.get("correct_index")
            if not block.get("question") or len(opts) < 2 or not isinstance(ci, int) or not (0 <= ci < len(opts)):
                return
            ctx = (block.get("context") or "").strip()
            qtext = f"{ctx}\n\n{block['question']}" if ctx else block["question"]
            focused[qid] = {
                "id": qid,
                "kc": kc_code,
                "cau": qtext,
                "lua_chon": list(opts),
                "dap_an": ci,
                "giai_thich": explain,
                "_w": weight,
                "_class_pct": class_pct,
                "_approved": True,
            }

        # ĐÚNG những câu giảng viên đã duyệt trên màn hình Bước 2 (Phần 1 + Phần 2 + các câu bổ sung GV duyệt)
        _add(f"iv_{kc_code}_main", intervention.get("scenario") or {}, 10.0)
        _add(f"iv_{kc_code}_transfer", intervention.get("transfer_scenario") or {}, 10.0)
        for idx, eq in enumerate(intervention.get("extra_questions") or []):
            _add(f"iv_{kc_code}_extra_{idx + 1}", eq, 10.0)

        if not focused:
            raise ValueError("Chưa có câu hỏi hợp lệ nào được giảng viên duyệt.")

        QUESTIONS = focused
        added = len(focused)
        FOCUS_INFO.update({
            "day": int(day) if day is not None else None,
            "kc_code": kc_code,
            "topic": intervention.get("topic") or kc_code,
            "approved": True,
            "custom_count": added,
            "pre_test_pct": class_pct,
        })
        # Số cửa khớp với độ khó mê cung 25x17 (vẫn chỉ dùng đúng các câu giảng viên đã duyệt)
        GAME.reset(n_gates=min(10, max(4, added * 3)))
        GAME._log("Đã nạp %d câu hỏi giảng viên duyệt cho chủ đề %s" % (added, intervention.get("topic") or kc_code), "big")
        return {"ok": True, "focus": dict(FOCUS_INFO), "added": added}


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


# ------------------------------------------------------------------ mê cung (5 bản đồ + đích ngẫu nhiên)

MAPS = [
    {
        "id": "classic",
        "name": "Mê cung Vũ trụ",
        "braid": 0.09,
        "theme": {"bg": "#151a45", "f1": "#232a66", "f2": "#262e70", "wS1": "#5f3dc4", "wS2": "#3b2a8f", "wT1": "#b197fc", "wT2": "#7950f2"},
    },
    {
        "id": "corridor",
        "name": "Rừng Ngọc Lục Bảo",
        "braid": 0.04,
        "theme": {"bg": "#0b2421", "f1": "#123832", "f2": "#164039", "wS1": "#087f5b", "wS2": "#064e3b", "wT1": "#63e6be", "wT2": "#12b886"},
    },
    {
        "id": "chambers",
        "name": "Đại sảnh Cổ đại",
        "braid": 0.11,
        "theme": {"bg": "#24190d", "f1": "#362715", "f2": "#3d2c18", "wS1": "#d97706", "wS2": "#92400e", "wT1": "#ffd43b", "wT2": "#f59f00"},
    },
    {
        "id": "fortress",
        "name": "Pháo đài Băng giá",
        "braid": 0.14,
        "theme": {"bg": "#0c1e35", "f1": "#142d4c", "f2": "#173457", "wS1": "#1971c2", "wS2": "#114b82", "wT1": "#74c0fc", "wT2": "#339af0"},
    },
    {
        "id": "labyrinth",
        "name": "Hầm ngục Hỏa diệm",
        "braid": 0.06,
        "theme": {"bg": "#260f16", "f1": "#3a1722", "f2": "#421b27", "wS1": "#c92a2a", "wS2": "#7f1d1d", "wT1": "#ff8787", "wT2": "#f03e3e"},
    },
]
MAP_BY_ID = {m["id"]: m for m in MAPS}


def _bfs_dist(t, start):
    H, W = len(t), len(t[0])
    dist = {start: 0}
    q = collections.deque([start])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and t[ny][nx] == 0 and (nx, ny) not in dist:
                dist[(nx, ny)] = d
                q.append((nx, ny))
    return dist


def _gen_maze(seed, n_gates=None, map_id=None):
    rnd = random.Random(seed)
    chosen = MAP_BY_ID.get(map_id) if map_id in MAP_BY_ID else rnd.choice(MAPS)
    mid = chosen["id"]
    gate_target = int(n_gates) if n_gates else N_GATES
    W, H = 2 * CELLS_W + 1, 2 * CELLS_H + 1
    t = [[1] * W for _ in range(H)]

    # 1. Sinh khung mê cung theo từng kiểu bản đồ (Growing Tree: DFS / Prim / kết hợp)
    sx, sy = rnd.randrange(CELLS_W), rnd.randrange(CELLS_H)
    seen = {(sx, sy)}
    active = [(sx, sy)]
    t[2 * sy + 1][2 * sx + 1] = 0
    while active:
        if mid == "corridor":
            idx = len(active) - 1  # DFS thuần -> hành lang dài quanh co
        elif mid == "fortress":
            idx = len(active) - 1 if rnd.random() < 0.45 else rnd.randrange(len(active))  # nhiều ngã tư phân nhánh
        elif mid == "labyrinth":
            idx = len(active) - 1 if rnd.random() < 0.7 else 0  # trộn BFS/DFS -> nhiều ngõ cụt bẫy
        else:
            idx = len(active) - 1 if rnd.random() < 0.85 else rnd.randrange(len(active))
        cx, cy = active[idx]
        nb = [(cx + dx, cy + dy, dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if 0 <= cx + dx < CELLS_W and 0 <= cy + dy < CELLS_H and (cx + dx, cy + dy) not in seen]
        if not nb:
            active.pop(idx)
            continue
        nx, ny, dx, dy = rnd.choice(nb)
        t[2 * cy + 1 + dy][2 * cx + 1 + dx] = 0
        t[2 * ny + 1][2 * nx + 1] = 0
        seen.add((nx, ny))
        active.append((nx, ny))

    # 2. Đặc trưng địa hình riêng từng bản đồ
    if mid == "chambers":
        # Đục 3–4 đại sảnh 3x3 rộng nối với hành lang -> tạo điểm chạm trán bất ngờ
        for _ in range(4):
            rx = rnd.randrange(1, CELLS_W - 2) * 2 + 1
            ry = rnd.randrange(1, CELLS_H - 2) * 2 + 1
            for dy in range(3):
                for dx in range(3):
                    if 1 <= rx + dx < W - 1 and 1 <= ry + dy < H - 1:
                        t[ry + dy][rx + dx] = 0
    elif mid == "fortress":
        # Mở một vòng hành lang bao quanh ở lớp ngoài để dễ bọc lót / rượt đuổi
        for x in range(1, W - 1):
            if rnd.random() < 0.35:
                t[1][x] = 0
            if rnd.random() < 0.35:
                t[H - 2][x] = 0

    braid = chosen["braid"]
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if t[y][x] == 1 and ((x % 2 == 1 and y % 2 == 0) or (x % 2 == 0 and y % 2 == 1)) and rnd.random() < braid:
                t[y][x] = 0

    floor = [(x, y) for y in range(H) for x in range(W) if t[y][x] == 0]
    center = (W // 2, H // 2)

    # 3. Đích đến NGẪU NHIÊN trên toàn bản đồ (không bắt buộc nằm ở trung tâm!)
    odd_floor = [p for p in floor if p[0] % 2 == 1 and p[1] % 2 == 1] or floor
    non_center = [p for p in odd_floor if abs(p[0] - center[0]) + abs(p[1] - center[1]) >= 4]
    goal = rnd.choice(non_center or odd_floor)

    # 4. Dùng BFS từ đích để chọn điểm xuất phát công bằng (đủ xa đích và chắc chắn đi tới được)
    dist = _bfs_dist(t, goal)
    reachable = [p for p in odd_floor if p in dist and p != goal]
    max_d = max((dist[p] for p in reachable), default=1)
    far_pool = [p for p in reachable if dist[p] >= int(max_d * 0.58)]
    if len(far_pool) < 8:
        far_pool = sorted(reachable, key=lambda p: -dist[p])[:max(12, len(reachable) // 2)]
    rnd.shuffle(far_pool)

    def near(p, qs, d):
        return any(abs(p[0] - q[0]) + abs(p[1] - q[1]) <= d for q in qs)

    spawns = []
    for min_gap in (4, 2, 0):
        for p in far_pool:
            if len(spawns) >= 8:
                break
            if p not in spawns and not near(p, spawns, min_gap):
                spawns.append(p)
        if len(spawns) >= 8:
            break
    if not spawns:
        spawns = [reachable[0] if reachable else (1, 1)]

    def corridor(x, y):
        h = t[y][x - 1] == 0 and t[y][x + 1] == 0 and t[y - 1][x] == 1 and t[y + 1][x] == 1
        v = t[y - 1][x] == 0 and t[y + 1][x] == 0 and t[y][x - 1] == 1 and t[y][x + 1] == 1
        return h or v

    cand = [p for p in floor if p in dist and corridor(*p) and not near(p, spawns + [goal], 2)]
    rnd.shuffle(cand)
    gates = []
    for p in cand:
        if len(gates) >= gate_target:
            break
        if not near(p, gates, 2):
            gates.append(p)
    rest = [p for p in floor if p in dist and p not in gates and not near(p, spawns + [goal], 2)]
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
    return {
        "w": W, "h": H, "tiles": t, "goal": list(goal), "spawns": spawns,
        "gates": [list(g) for g in gates],
        "boxes": {"%d,%d" % p: kinds[i % len(kinds)] for i, p in enumerate(boxes)},
        "map_id": chosen["id"],
        "map_name": chosen["name"],
        "theme": dict(chosen["theme"]),
    }


# ------------------------------------------------------------------ trạng thái ván

class Game:
    def __init__(self):
        self.map_pref = "random"
        self.reset()

    def reset(self, n_gates=None, map_id=None, keep_players=False):
        self.round_id = uuid.uuid4().hex[:6]
        if map_id is not None:
            self.map_pref = map_id if map_id in MAP_BY_ID else "random"
        pick_map = None if self.map_pref == "random" else self.map_pref
        gates_count = n_gates if n_gates is not None else (min(10, max(4, FOCUS_INFO.get("custom_count", 2) * 3)) if FOCUS_INFO.get("approved") else N_GATES)
        self.maze = _gen_maze(random.randrange(10 ** 9), n_gates=gates_count, map_id=pick_map)
        self.phase = "lobby"
        if keep_players and self.players:
            for idx, p in enumerate(self.players.values()):
                sp = self.maze["spawns"][idx % len(self.maze["spawns"])]
                p.update(x=sp[0], y=sp[1], status="lobby", opened=[], asked=[], shield=0,
                         boost_until=0, frozen_until=0, last_move=0, q=None, rank=None, points=0,
                         correct=0, wrong=0)
        else:
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
        self._log("%s đã vào phòng" % name)
        return {"pid": pid}

    def start(self):
        if self.phase != "lobby":
            return {"error": "Ván đã bắt đầu."}
        if not self.players:
            return {"error": "Chưa có ai vào phòng."}
        self.phase, self.started_at = "playing", _now()
        for p in self.players.values():
            p["status"] = "playing"
        self._log("Bắt đầu trên bản đồ %s — đích đến ẩn ngẫu nhiên!" % self.maze.get("map_name", "Mê cung"), "big")
        return {"ok": True}

    def end(self):
        if self.phase == "playing":
            for p in self.players.values():
                if p["status"] in ("playing", "question", "duel"):
                    _record(p["user"], p["name"], self.round_id, None, 0, "chưa về đích")
            self.phase = "ended"
            self._log("Giảng viên đã kết thúc ván.", "big")
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
                self._gate_fail(p, "%s hết giờ trả lời ở cửa câu hỏi" % p["name"])
        for d in list(self.duels.values()):
            if now > d["deadline"]:
                d["draws"] += 1
                if d["draws"] >= 3:
                    w = random.choice([d["a"], d["b"]])
                    self._finish_duel(d, w, "Hoà 3 lượt — chọn ngẫu nhiên %s" % self.players[w]["name"])
                else:
                    self._log("Hết giờ đấu — chuyển sang câu mới")
                    self._new_duel_question(d)
        alive = [p for p in self.players.values() if p["status"] in ("playing", "question", "duel")]
        if not alive:
            self.phase = "ended"
            self._log("Ván chơi đã kết thúc.", "big")

    # ---- di chuyển (hỗ trợ gom bước & trả ngay state để giảm lag mạng)
    def _step_one(self, p, dx, dy, now):
        if self.phase != "playing" or p["status"] != "playing":
            return False
        if now < p["frozen_until"]:
            return False
        nx, ny = p["x"] + dx, p["y"] + dy
        if not (0 <= nx < self.maze["w"] and 0 <= ny < self.maze["h"]) or self.maze["tiles"][ny][nx] == 1:
            return False
        if [nx, ny] in self.maze["gates"]:
            if [nx, ny] not in p["opened"]:
                if p["shield"] > 0:
                    p["shield"] -= 1
                    p["opened"].append([nx, ny])
                    self._log("%s dùng khiên vượt cửa" % p["name"])
                else:
                    item, right = _present(_pick_question(p["asked"])["id"])
                    p["asked"].append(item["id"])
                    p["q"] = {"kind": "gate", "item": item, "right": right, "gate": [nx, ny], "deadline": now + Q_TIME}
                    p["status"] = "question"
                    return True
        p["x"], p["y"] = nx, ny
        self._after_step(p)
        return True

    def move(self, pid, dx, dy):
        return self.move_batch(pid, [(dx, dy)])

    def move_batch(self, pid, steps):
        p = self.players.get(pid)
        if not p or self.phase != "playing" or p["status"] != "playing":
            return {"ok": False, "state": self.state(pid, host=False) if p else None}
        now = _now()
        if now < p["frozen_until"]:
            return {"ok": False, "why": "frozen", "state": self.state(pid, host=False)}
        gap = (BOOST_MS if now < p["boost_until"] else MOVE_MS) / 1000.0
        # Tính số bước tối đa hợp lệ theo thời gian đã trôi (cho phép gom tối đa 4 bước khi mạng có độ trễ)
        elapsed = max(0.0, now - p["last_move"])
        budget = min(4, max(1 if elapsed >= gap * 0.65 else 0, int(elapsed / gap) + (1 if p["last_move"] == 0 else 0)))
        if budget <= 0:
            return {"ok": False, "state": self.state(pid, host=False)}
        moved = 0
        for dx, dy in steps[:budget]:
            if not self._step_one(p, dx, dy, now):
                break
            moved += 1
            if p["status"] != "playing":
                break
        if moved > 0:
            p["last_move"] = now
        return {"ok": moved > 0, "moved": moved, "state": self.state(pid, host=False)}

    def _after_step(self, p):
        now = _now()
        key = "%d,%d" % (p["x"], p["y"])
        kind = self.maze["boxes"].pop(key, None)
        if kind:
            self._log("%s mở hộp may mắn: %s" % (p["name"], BOX_TEXT[kind]), "luck")
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
            self._log("%s trả lời đúng và mở cửa" % p["name"])
            self._after_step(p)
            return {"ok": True, "correct": True, "giai_thich": expl}
        p["wrong"] += 1
        self._gate_fail(p, "%s trả lời sai, tạm dừng %d giây" % (p["name"], PENALTY_WRONG))
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
        self._log("⚔️ %s gặp %s — bắt đầu đấu tốc độ" % (a["name"], b["name"]), "duel")
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
            self._finish_duel(d, p["pid"], "%s trả lời đúng trước (%.1f giây)" % (p["name"], secs))
            return {"ok": True, "correct": True, "won": True}
        p["wrong"] += 1
        d["wrong"].append(p["pid"])
        if len(d["wrong"]) == 2:
            d["draws"] += 1
            if d["draws"] >= 3:
                w = random.choice([d["a"], d["b"]])
                self._finish_duel(d, w, "Cả hai sai 3 lượt — chọn ngẫu nhiên %s" % self.players[w]["name"])
            else:
                self._log("Cả hai trả lời sai — chuyển sang câu mới")
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
                "gates": m["gates"], "map_id": m.get("map_id"), "map_name": m.get("map_name"),
                "theme": m.get("theme")}

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
        if host or (me and p["pid"] == me["pid"]):
            v["correct"] = p["correct"]
            v["wrong"] = p["wrong"]
        if not (me and p["pid"] == me["pid"]) and not self._sees(me, host, p["x"], p["y"]):
            v["x"] = v["y"] = None
        return v

    def _analytics(self):
        """Tính số liệu & phân bố mức độ hiểu trong ván để vẽ biểu đồ giống màn hình Đánh giá."""
        total_players = len(self.players)
        finished_count = sum(1 for p in self.players.values() if p["status"] == "finished")
        total_ans = sum(v["hoi"] for v in self.qstats.values())
        total_ok = sum(v["dung"] for v in self.qstats.values())
        game_pct = round(total_ok / total_ans * 100, 1) if total_ans else None

        pre_pct = FOCUS_INFO.get("pre_test_pct")
        if pre_pct is None:
            pcts = [QUESTIONS[k]["_class_pct"] for k in self.qstats if k in QUESTIONS and QUESTIONS[k].get("_class_pct") is not None]
            if not pcts:
                pcts = [q["_class_pct"] for q in QUESTIONS.values() if q.get("_class_pct") is not None]
            pre_pct = round(sum(pcts) / len(pcts), 1) if pcts else None

        delta_pct = round(game_pct - pre_pct, 1) if (game_pct is not None and pre_pct is not None) else None

        mastered = developing = struggling = unanswered = 0
        for p in self.players.values():
            n = p["correct"] + p["wrong"]
            if n == 0:
                unanswered += 1
            else:
                ratio = p["correct"] / n
                if ratio >= 0.75:
                    mastered += 1
                elif ratio >= 0.5:
                    developing += 1
                else:
                    struggling += 1

        return {
            "total_players": total_players,
            "answered_players": total_players - unanswered,
            "finished_count": finished_count,
            "total_answers": total_ans,
            "total_correct": total_ok,
            "pre_test_pct": pre_pct,
            "game_pct": game_pct,
            "delta_pct": delta_pct,
            "mastered_count": mastered,
            "developing_count": developing,
            "struggling_count": struggling,
            "unanswered_count": unanswered,
        }

    def state(self, pid=None, host=False):
        now = _now()
        me = self.players.get(pid) if pid else None
        if me:
            me["seen"] = now
        out = {"round": self.round_id, "phase": self.phase, "now": now,
               "elapsed": (now - self.started_at) if self.started_at else 0,
               "focus": dict(FOCUS_INFO),
               "map_id": self.maze.get("map_id"),
               "map_name": self.maze.get("map_name"),
               "map_pref": self.map_pref,
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
                  "lop_pct": QUESTIONS[k]["_class_pct"]} for k, v in self.qstats.items() if k in QUESTIONS],
                key=lambda r: r["dung"] / max(1, r["hoi"]))
            out["analytics"] = self._analytics()
            out["maps"] = [{"id": m["id"], "name": m["name"]} for m in MAPS]
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
        can_teach_req = bool(local or not TEACHER_LOCAL_ONLY or is_valid_host_key(body.get("hk")))
        # ---- tài khoản
        if method == "GET" and path == "/game/api/auth/me":
            return {"user": {"ten": sess["ten"], "role": sess["role"]} if sess else None,
                    "can_teach": can_teach_req}
        if method == "POST" and path == "/game/api/auth/role":
            return choose_role(body.get("role"), body.get("ten"), can_teach_req)
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
            dir_map = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
            raw_dirs = body.get("dirs")
            if isinstance(raw_dirs, list) and raw_dirs:
                steps = [dir_map[d] for d in raw_dirs[:4] if d in dir_map]
                return GAME.move_batch(pid, steps) if (pid and steps) else {"ok": False}
            dx, dy = dir_map.get(body.get("dir"), (0, 0))
            return GAME.move(pid, dx, dy) if (pid and (dx or dy)) else {"ok": False}
        if method == "POST" and path == "/game/api/answer":
            return GAME.answer(pid, body.get("qid"), body.get("choice", -1)) if pid else {"ok": False}
        # ---- chỉ giảng viên
        if path in ("/game/api/profiles", "/game/api/host/start", "/game/api/host/end", "/game/api/host/new", "/game/api/host/map") and not teacher:
            return {"error": "Chỉ giảng viên làm được việc này."}
        if method == "GET" and path == "/game/api/profiles":
            return {"profiles": profiles_view(), "da_duyet_cau_hoi": bool(FOCUS_INFO["approved"])}
        if method == "POST" and path == "/game/api/host/start":
            return GAME.start()
        if method == "POST" and path == "/game/api/host/end":
            return GAME.end()
        if method == "POST" and path == "/game/api/host/map":
            if GAME.phase != "lobby":
                return {"error": "Chỉ đổi bản đồ khi đang ở phòng chờ."}
            GAME.reset(map_id=body.get("map", "random"), keep_players=True)
            return {"ok": True, "map_id": GAME.maze.get("map_id"), "map_name": GAME.maze.get("map_name")}
        if method == "POST" and path == "/game/api/host/new":
            GAME.reset(map_id=body.get("map"))
            return {"ok": True, "map_id": GAME.maze.get("map_id"), "map_name": GAME.maze.get("map_name")}
    return None
