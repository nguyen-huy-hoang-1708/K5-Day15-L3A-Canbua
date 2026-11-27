"""Lưu trữ SQLite cho Canbua Learning Intervention Engine (Detect → Intervene → Evaluate)."""
import datetime
import json
import os
import random
import sqlite3
import string

from intervention_engine import evaluate_submission

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "rescue.db")


_INITIALIZED_DB = None


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10.0)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    global _INITIALIZED_DB
    db_key = os.path.abspath(str(DB_PATH))
    if _INITIALIZED_DB == db_key and os.path.exists(db_key):
        return
    with _conn() as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS intervention_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_code TEXT UNIQUE NOT NULL,
                day INTEGER NOT NULL,
                kc_code TEXT NOT NULL,
                preclass_correct INTEGER NOT NULL,
                preclass_total INTEGER NOT NULL,
                preclass_pct REAL NOT NULL,
                intervention_json TEXT NOT NULL,
                approved INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intervention_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_code TEXT NOT NULL,
                student_name TEXT NOT NULL DEFAULT '',
                main_choice INTEGER NOT NULL,
                main_correct INTEGER NOT NULL,
                main_explanation TEXT NOT NULL,
                transfer_choice INTEGER NOT NULL,
                transfer_correct INTEGER NOT NULL,
                transfer_explanation TEXT NOT NULL,
                explanation_score INTEGER NOT NULL,
                learning_status TEXT NOT NULL,
                extra_answers_json TEXT NOT NULL DEFAULT '[]',
                is_demo_simulated INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        cols = {r["name"] for r in con.execute("PRAGMA table_info(intervention_submissions)").fetchall()}
        if "extra_answers_json" not in cols:
            con.execute("ALTER TABLE intervention_submissions ADD COLUMN extra_answers_json TEXT NOT NULL DEFAULT '[]'")
        if "student_name" not in cols:
            con.execute("ALTER TABLE intervention_submissions ADD COLUMN student_name TEXT NOT NULL DEFAULT ''")
    _INITIALIZED_DB = db_key


def _new_code() -> str:
    return "CB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


def create_session(day: int, kc_code: str, preclass_meta: dict, intervention: dict) -> dict:
    init_db()
    code = _new_code()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with _conn() as con:
        con.execute(
            """INSERT INTO intervention_sessions
               (session_code, day, kc_code, preclass_correct, preclass_total, preclass_pct, intervention_json, approved, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                code,
                int(day),
                kc_code,
                int(preclass_meta.get("so_dung_lan_dau") or 0),
                int(preclass_meta.get("so_lan_tra_loi_dau") or 0),
                float(preclass_meta.get("ti_le_dung_pct") or 0.0),
                json.dumps(intervention, ensure_ascii=False),
                now,
            ),
        )
    return get_session_summary(code)


def list_sessions(limit: int = 20) -> list:
    init_db()
    with _conn() as con:
        rows = con.execute(
            """SELECT s.session_code, s.day, s.kc_code, s.preclass_pct, s.created_at,
                      COUNT(b.id) AS total_submissions,
                      SUM(CASE WHEN b.id IS NOT NULL AND b.is_demo_simulated = 0 THEN 1 ELSE 0 END) AS real_submissions
               FROM intervention_sessions s
               LEFT JOIN intervention_submissions b ON b.session_code = s.session_code
               GROUP BY s.id
               ORDER BY s.id DESC
               LIMIT ?""",
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


def submit_learning_activity(
    session_code: str,
    main_choice: int,
    main_explanation: str,
    transfer_choice: int,
    transfer_explanation: str,
    is_demo_simulated: bool = False,
    extra_choices: list = None,
    student_name: str = "",
) -> dict:
    init_db()
    code = session_code.strip().upper()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with _conn() as con:
        row = con.execute("SELECT * FROM intervention_sessions WHERE session_code = ?", (code,)).fetchone()
        if not row:
            raise ValueError("Không tìm thấy phiên học " + code)
        intervention = json.loads(row["intervention_json"])
        ev = evaluate_submission(
            intervention, main_choice, main_explanation, transfer_choice, transfer_explanation, extra_choices=extra_choices
        )
        cnt = con.execute(
            "SELECT COUNT(*) FROM intervention_submissions WHERE session_code = ?", (code,)
        ).fetchone()[0]
        clean_name = (student_name or "").strip()[:60]
        if not clean_name:
            clean_name = f"Demo #{cnt + 1}" if is_demo_simulated else f"Học viên #{cnt + 1}"

        con.execute(
            """INSERT INTO intervention_submissions
               (session_code, student_name, main_choice, main_correct, main_explanation,
                transfer_choice, transfer_correct, transfer_explanation,
                explanation_score, learning_status, extra_answers_json, is_demo_simulated, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                clean_name,
                int(main_choice),
                1 if ev["main_correct"] else 0,
                (main_explanation or "").strip()[:500],
                int(transfer_choice),
                1 if ev["transfer_correct"] else 0,
                (transfer_explanation or "").strip()[:500],
                int(ev["explanation_score"]),
                ev["learning_status"],
                json.dumps([int(x) for x in (extra_choices or [])]),
                1 if is_demo_simulated else 0,
                now,
            ),
        )
    return {
        "session_code": code,
        "evaluation": ev,
        "summary": get_session_summary(code),
    }


def simulate_demo_responses(session_code: str, count: int = 10) -> dict:
    """Chèn lượt minh hoạ giao diện (tách riêng bằng is_demo_simulated=1)."""
    init_db()
    code = session_code.strip().upper()
    with _conn() as con:
        row = con.execute("SELECT intervention_json FROM intervention_sessions WHERE session_code = ?", (code,)).fetchone()
        if not row:
            raise ValueError("Không tìm thấy phiên " + code)
        iv = json.loads(row["intervention_json"])

    sc = iv["scenario"]
    tr = iv["transfer_scenario"]
    sc_right, tr_right = int(sc["correct_index"]), int(tr["correct_index"])
    sc_wrongs = [i for i in range(len(sc["options"])) if i != sc_right]
    tr_wrongs = [i for i in range(len(tr["options"])) if i != tr_right]

    rng = random.Random()
    sample_good_exp = "Cần suy luận nhiều bước vì có nhiều yếu tố; tác vụ đơn giản nên dùng code để tránh tốn token."
    sample_mid_exp = "Tình huống này cần phân tích nguyên nhân kỹ hơn."
    sample_weak_exp = "Em chọn theo cảm giác."

    extra_qs = iv.get("extra_questions") or []
    for _ in range(max(1, min(25, int(count)))):
        main_ok = rng.random() < 0.80
        # Transfer khó hơn một chút để minh hoạ rõ sự khác biệt Post-test vs Transfer!
        transfer_ok = rng.random() < (0.78 if main_ok else 0.35)
        mc = sc_right if main_ok else rng.choice(sc_wrongs or [sc_right])
        tc = tr_right if transfer_ok else rng.choice(tr_wrongs or [tr_right])
        extra_picks = []
        for eq in extra_qs:
            er = int(eq["correct_index"])
            ew = [i for i in range(len(eq["options"])) if i != er]
            extra_picks.append(er if rng.random() < 0.75 else rng.choice(ew or [er]))
        exp_m = sample_good_exp if (main_ok and transfer_ok) else (sample_mid_exp if main_ok else sample_weak_exp)
        exp_t = sample_mid_exp if transfer_ok else sample_weak_exp
        submit_learning_activity(code, mc, exp_m, tc, exp_t, is_demo_simulated=True, extra_choices=extra_picks)
    return get_session_summary(code)


def clear_demo_responses(session_code: str) -> dict:
    init_db()
    code = session_code.strip().upper()
    with _conn() as con:
        con.execute("DELETE FROM intervention_submissions WHERE session_code = ? AND is_demo_simulated = 1", (code,))
    return get_session_summary(code)


def get_session_summary(session_code: str) -> dict:
    init_db()
    code = session_code.strip().upper()
    with _conn() as con:
        row = con.execute("SELECT * FROM intervention_sessions WHERE session_code = ?", (code,)).fetchone()
        if not row:
            return {}
        subs = [
            dict(r)
            for r in con.execute(
                "SELECT * FROM intervention_submissions WHERE session_code = ? ORDER BY id ASC",
                (code,),
            ).fetchall()
        ]

    iv = json.loads(row["intervention_json"])
    total = len(subs)
    real_n = sum(1 for s in subs if not s["is_demo_simulated"])
    demo_n = sum(1 for s in subs if s["is_demo_simulated"])

    main_ok = sum(s["main_correct"] for s in subs)
    tr_ok = sum(s["transfer_correct"] for s in subs)
    avg_exp = round(sum(s["explanation_score"] for s in subs) / total, 2) if total else None
    mastered_n = sum(1 for s in subs if s["learning_status"] == "mastered")
    recovering_n = sum(1 for s in subs if s["learning_status"] == "recovering")
    surface_only = sum(1 for s in subs if s["learning_status"] == "surface_only")
    persistent_n = sum(1 for s in subs if s["learning_status"] == "persistent_error")

    post_pct = round(main_ok / total * 100, 1) if total else None
    transfer_pct = round(tr_ok / total * 100, 1) if total else None
    pre_pct = float(row["preclass_pct"])

    # Phân bố lựa chọn sai ở Tình huống chính, Transfer Test & câu thêm (nếu có)
    sc_opts = iv["scenario"]["options"]
    tr_opts = iv["transfer_scenario"]["options"]
    extra_qs = iv.get("extra_questions") or []
    sc_counts = [0] * len(sc_opts)
    tr_counts = [0] * len(tr_opts)
    extra_counts = [[0] * len(eq.get("options") or []) for eq in extra_qs]
    for s in subs:
        if 0 <= s["main_choice"] < len(sc_counts):
            sc_counts[s["main_choice"]] += 1
        if 0 <= s["transfer_choice"] < len(tr_counts):
            tr_counts[s["transfer_choice"]] += 1
        try:
            ex = json.loads(s.get("extra_answers_json") or "[]")
        except Exception:
            ex = []
        for i, cnts in enumerate(extra_counts):
            if i < len(ex) and isinstance(ex[i], int) and 0 <= ex[i] < len(cnts):
                cnts[ex[i]] += 1

    persistent_errors = []
    if total > 0:
        if surface_only > 0:
            persistent_errors.append(
                f"{surface_only}/{total} lượt đúng ví dụ chính nhưng sai Transfer Test — dấu hiệu mới nhớ mẫu, chưa vận dụng sang bối cảnh mới."
            )
        if persistent_n > 0:
            persistent_errors.append(
                f"{persistent_n}/{total} lượt sai cả hai tình huống — cần giảng lại khái niệm cốt lõi trước khi làm lab."
            )
        low_exp = sum(1 for s in subs if s["explanation_score"] == 0)
        if low_exp > 0:
            persistent_errors.append(
                f"{low_exp}/{total} lượt giải thích chưa chạm rubric (0/2 điểm) — cần yêu cầu học viên nêu rõ lý do chọn."
            )

    return {
        "session_code": row["session_code"],
        "day": row["day"],
        "kc_code": row["kc_code"],
        "approved": bool(row["approved"]),
        "created_at": row["created_at"],
        "intervention": iv,
        "metrics": {
            "pre_test_correct": row["preclass_correct"],
            "pre_test_total": row["preclass_total"],
            "pre_test_pct": pre_pct,
            "participants": total,
            "real_participants": real_n,
            "demo_participants": demo_n,
            "post_test_correct": main_ok,
            "post_test_pct": post_pct,
            "transfer_correct": tr_ok,
            "transfer_pct": transfer_pct,
            "avg_explanation_score": avg_exp,
            "mastered_count": mastered_n,
            "recovering_count": recovering_n,
            "surface_only_count": surface_only,
            "persistent_error_count": persistent_n,
        },
        "distributions": {
            "scenario_counts": sc_counts,
            "transfer_counts": tr_counts,
            "extra_counts": extra_counts,
        },
        "submissions": [
            {
                "id": s["id"],
                "student_name": s.get("student_name") or f"Lượt #{i + 1}",
                "main_choice": s["main_choice"],
                "main_correct": bool(s["main_correct"]),
                "main_explanation": s["main_explanation"],
                "transfer_choice": s["transfer_choice"],
                "transfer_correct": bool(s["transfer_correct"]),
                "transfer_explanation": s["transfer_explanation"],
                "explanation_score": s["explanation_score"],
                "learning_status": s["learning_status"],
                "is_demo_simulated": bool(s["is_demo_simulated"]),
                "created_at": s["created_at"],
            }
            for i, s in enumerate(subs)
        ],
        "persistent_errors": persistent_errors,
        "caveat": (
            "Lưu ý khoa học: Kết quả trước/sau là tín hiệu thay đổi sau hoạt động, chưa đủ để khẳng định "
            "hoạt động là nguyên nhân duy nhất tạo ra sự tiến bộ (cần nhóm đối chứng nếu muốn kết luận nhân quả)."
        ),
    }
