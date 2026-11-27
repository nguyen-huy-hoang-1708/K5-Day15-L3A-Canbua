"""Học viên giả + giảng viên giả cho video demo trò chơi (chỉ dùng khi quay video, không dùng khi chơi thật).

python3 slides/record/game_bots.py http://localhost:8003 An
- Giảng viên giả: mở ván mới, chờ đủ người (gồm nhân vật chính "An" do video điều khiển) rồi bấm bắt đầu;
  khi An về đích / bị loại (hoặc quá 150 giây) thì kết thúc ván.
- Bình: đuổi theo An để tạo màn đấu tay đôi (trả lời chậm hơn An).
- Chi, Dũng: đi về đích; Dũng đi chậm và đôi khi trả lời sai ở cửa.
Bot đọc đáp án từ data/game_questions.json (server không gửi đáp án xuống) — chỉ để dựng cảnh quay.
"""
import json
import os
import random
import sys
import threading
import time
import urllib.request
from collections import deque

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8003"
HERO = sys.argv[2] if len(sys.argv) > 2 else "An"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BANK = {q["cau"]: q["lua_chon"][q["dap_an"]] for q in json.load(open(os.path.join(ROOT, "data", "game_questions.json"), encoding="utf-8"))["cau_hoi"]}
DIRS = {(1, 0): "right", (-1, 0): "left", (0, 1): "down", (0, -1): "up"}
STOP = threading.Event()


def call(path, body=None, tok=""):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "X-Token": tok},
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def path_to(tiles, a, b, avoid=None):
    q, prev = deque([a]), {a: None}
    while q:
        c = q.popleft()
        if c == b:
            break
        for dx, dy in DIRS:
            n = (c[0] + dx, c[1] + dy)
            if tiles[n[1]][n[0]] == 0 and n not in prev and n != avoid:
                prev[n] = c
                q.append(n)
    if b not in prev:
        return []
    out, c = [], b
    while c:
        out.append(c)
        c = prev[c]
    return out[::-1]


def learner(name, color, target, step=0.2, think=(1.2, 2.0), wrong_rate=0.0, duel_think=(2.2, 3.0)):
    tok = call("/game/api/auth/role", {"role": "hoc_vien", "ten": name})["token"]
    pid = call("/game/api/join", {"color": color}, tok)["pid"]
    maze = None
    answered = None
    while not STOP.is_set():
        st = call("/game/api/state?pid=" + pid, tok=tok)
        me = st.get("me")
        if not me or me["status"] in ("out", "finished") or st["phase"] == "ended":
            break
        if st["phase"] != "playing":
            time.sleep(0.4)
            continue
        if maze is None:
            maze = call("/game/api/maze")
        q = me.get("question") or me.get("duel")
        if q:
            key = q["id"] + str(q.get("draws", ""))
            if answered == key or q.get("locked"):
                time.sleep(0.2)
                continue
            time.sleep(random.uniform(*(duel_think if me.get("duel") else think)))
            right = q["lua_chon"].index(BANK[q["cau"]])
            choice = right if random.random() >= wrong_rate or me.get("duel") else (right + 1) % len(q["lua_chon"])
            call("/game/api/answer", {"pid": pid, "qid": q["id"], "choice": choice}, tok)
            answered = key
            continue
        if me["frozen"] > 0:
            time.sleep(0.3)
            continue
        mine = next(p for p in st["players"] if p["pid"] == pid)
        if target == "goal":
            goal = tuple(maze["goal"])
        else:
            hero = next((p for p in st["players"] if p["name"] == target and p["status"] == "playing"), None)
            if not hero or hero["x"] is None:  # chưa thấy An trong tầm nhìn: hỏi vị trí qua giảng viên giả
                hero = next((p for p in TEACHER_VIEW.get("players", []) if p["name"] == target), None)
            if not hero or hero["status"] not in ("playing", "question"):
                time.sleep(0.3)
                continue
            goal = (hero["x"], hero["y"])
        pth = path_to(maze["tiles"], (mine["x"], mine["y"]), goal,
                      avoid=None if target == "goal" else tuple(maze["goal"]))  # đi đuổi thì không cắt qua ô đích
        if target != "goal" and len(pth) <= 3:  # đã sát An: đứng chờ để An bước vào ô (không lướt qua nhau)
            time.sleep(0.2)
            continue
        if len(pth) >= 2:
            d = DIRS[(pth[1][0] - pth[0][0], pth[1][1] - pth[0][1])]
            call("/game/api/move", {"pid": pid, "dir": d}, tok)
        time.sleep(step)


TEACHER_VIEW = {}


def teacher():
    tok = call("/game/api/auth/role", {"role": "giang_vien"})["token"]
    t0 = time.time()
    while time.time() - t0 < 60:  # chờ An vào phòng
        st = call("/game/api/state?host=1", tok=tok)
        names = [p["name"] for p in st["players"]]
        if HERO in names and len(names) >= 4:
            break
        time.sleep(0.4)
    time.sleep(3.0)
    call("/game/api/host/start", {}, tok)
    t1 = time.time()
    while time.time() - t1 < 150:
        st = call("/game/api/state?host=1", tok=tok)
        TEACHER_VIEW.clear()
        TEACHER_VIEW.update(st)
        hero = next((p for p in st["players"] if p["name"] == HERO), None)
        if st["phase"] == "ended" or (hero and hero["status"] in ("finished", "out")):
            time.sleep(2.5)
            break
        time.sleep(0.3)
    call("/game/api/host/end", {}, tok)
    STOP.set()


if __name__ == "__main__":
    tok = call("/game/api/auth/role", {"role": "giang_vien"})["token"]
    call("/game/api/host/new", {}, tok)
    threads = [threading.Thread(target=teacher)]
    threads += [threading.Thread(target=learner, args=a, kwargs=k) for a, k in [
        (("Bình", "#ff6b6b", HERO), {"step": 0.17, "duel_think": (4.5, 5.5)}),
        (("Chi", "#4dabf7", "goal"), {"step": 0.6, "think": (2.5, 3.5), "wrong_rate": 0.4, "duel_think": (4.5, 5.5)}),
        (("Dũng", "#fcc419", "goal"), {"step": 0.7, "think": (3.0, 4.0), "wrong_rate": 0.5, "duel_think": (4.5, 5.5)}),
    ]]
    for t in threads:
        t.daemon = True
        t.start()
    threads[0].join()
    print("bots xong")
