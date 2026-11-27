"""AI-Powered Learning Intervention Engine (theo dexuatmoi.md).

Nguyên tắc thiết kế (§6):
- Code chịu trách nhiệm về dữ liệu, cấu trúc, kiểm tra tính nhất quán (Validation Layer) và chấm điểm rubric.
- AI chịu trách nhiệm thiết kế/tuỳ biến hoạt động can thiệp có cấu trúc (9 phần) khi bật chế độ AI,
  luôn neo chặt vào tài liệu kiến thức `data/kc_knowledge.json` và chờ giảng viên duyệt.
"""
import json
import os
import re

from ai import MODEL_PROVIDER, call_model
from tracing import note

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KC_KB_PATH = os.path.join(ROOT, "data", "kc_knowledge.json")

SYSTEM_INTERVENTION = """Bạn là AI Instructional Designer cho hệ thống Canbua (AI20K).
Nhiệm vụ: Dựa trên tài liệu kiến thức (KC Reference) được cung cấp, tạo hoạt động can thiệp học tập có cấu trúc JSON
gồm tình huống thực tế, hoạt động đối chiếu, phản hồi điều chỉnh cách hiểu và tình huống chuyển giao (Transfer Test).
QUY TẮC:
1. Chỉ bám sát tài liệu kiến thức được cung cấp, không bịa kiến thức ngoài nguồn.
2. Mọi giả thuyết về nguyên nhân sai phải ghi rõ là "giả thuyết cần kiểm chứng".
3. Tình huống Transfer Test phải KHÁC bối cảnh với tình huống chính nhưng kiểm tra cùng kiến thức cốt lõi.
4. Trả về DUY NHẤT một JSON hợp lệ giữ đúng cấu trúc khoá của mẫu đầu vào."""


_KB_CACHE = {"key": None, "data": {}}


def _load_kb() -> dict:
    if not os.path.exists(KC_KB_PATH):
        return {}
    st = os.stat(KC_KB_PATH)
    key = (st.st_mtime_ns, st.st_size)
    if _KB_CACHE["key"] == key:
        return _KB_CACHE["data"]
    with open(KC_KB_PATH, encoding="utf-8") as f:
        data = json.load(f)
    _KB_CACHE["key"] = key
    _KB_CACHE["data"] = data
    return data


def _generic_intervention(kc_code: str, kc_meta: dict) -> dict:
    pretty = (kc_code or "Chủ đề").replace("_", " ").title()
    c = kc_meta.get("so_dung_lan_dau", "?")
    n = kc_meta.get("so_lan_tra_loi_dau", "?")
    pct = kc_meta.get("ti_le_dung_pct", "—")
    return {
        "kc_code": kc_code,
        "topic": f"Can thiệp kiến thức: {pretty}",
        "learning_objective": f"Hiểu rõ điều kiện áp dụng đúng của `{pretty}` và vận dụng được vào bối cảnh mới.",
        "prerequisites": "Đã xem bài giảng pre-class của ngày học tương ứng.",
        "concept_explanation": f"Chủ đề `{kc_code}` có tỉ lệ đúng lần đầu ở pre-class là {c}/{n} ({pct}%). Cần làm rõ bản chất khái niệm và ranh giới khi nào áp dụng đúng/sai.",
        "possible_misconceptions": [
            f"Giả thuyết (cần kiểm chứng): Học viên nhớ định nghĩa `{pretty}` nhưng chưa phân biệt được khi nào nên áp dụng và khi nào không phù hợp."
        ],
        "scenario": {
            "context": f"Tình huống đối chiếu về `{pretty}`: So sánh hai cách triển khai — Cách A áp dụng đúng điều kiện của `{pretty}`, Cách B áp dụng máy móc bỏ qua ràng buộc thực tế.",
            "question": f"Trong tình huống trên, cách tiếp cận nào áp dụng đúng bản chất của `{pretty}`?",
            "options": [
                "Cách A — kiểm tra rõ điều kiện áp dụng và mục tiêu trước khi triển khai",
                "Cách B — áp dụng mặc định cho mọi bài toán không cần xét điều kiện",
                "Bỏ qua khái niệm này và làm theo cảm tính",
            ],
            "correct_index": 0,
            "explanation_prompt": "Giải thích ngắn gọn (1–2 câu): Vì sao cách còn lại có thể gây lỗi?",
        },
        "comparison_approaches": [
            "Cách 1 (Áp dụng máy móc): Bỏ qua ràng buộc bối cảnh → dễ gây sai lệch hoặc lãng phí chi phí.",
            "Cách 2 (Áp dụng có căn cứ): Kiểm tra điều kiện phù hợp rồi mới áp dụng và đo kiểm kết quả.",
        ],
        "feedback": {
            "why_wrong": "Áp dụng kiến thức mà không kiểm tra điều kiện phù hợp thường dẫn tới lỗi sai hệ thống hoặc lãng phí tài nguyên.",
            "relearn": f"Luôn gắn `{pretty}` với câu hỏi: 'Trong bối cảnh nào cách này hiệu quả, và khi nào cần giải pháp khác?'",
            "when_to_apply": "Kiểm tra điều kiện biên trước khi đưa vào triển khai thực tế.",
        },
        "transfer_scenario": {
            "context": f"Tình huống mới (Transfer Test): Một đội sản phẩm khác gặp bài toán mới hoàn toàn nhưng cùng nguyên lý cốt lõi của `{pretty}` với yêu cầu kiểm soát chi phí và độ tin cậy.",
            "question": "Bước đầu tiên đội sản phẩm nên làm để áp dụng đúng kiến thức này là gì?",
            "options": [
                "Xác định rõ tiêu chí phù hợp và kiểm thử trên trường hợp thực tế trước khi mở rộng",
                "Sao chép y nguyên cấu hình cũ mà không đánh giá bối cảnh mới",
                "Không cần đo lường sau khi áp dụng",
            ],
            "correct_index": 0,
            "explanation_prompt": "Giải thích ngắn gọn (1 câu): Điểm tương đồng cốt lõi giữa tình huống mới và ví dụ trước là gì?",
        },
        "assessment_rubric": {
            "criteria": "Đạt 2/2 nếu giải thích nêu rõ được điều kiện áp dụng và lý do tránh áp dụng máy móc.",
            "key_concepts": [
                ["điều kiện", "bối cảnh", "phù hợp", "kiểm tra", "tiêu chí"],
                ["máy móc", "lỗi", "chi phí", "rủi ro", "sai"],
            ],
        },
    }


def validate_intervention(item: dict) -> dict:
    """Validation Layer (§6): kiểm tra tính đầy đủ, đáp án hợp lệ và tách biệt bối cảnh Transfer."""
    errors = []
    req = ("learning_objective", "concept_explanation", "possible_misconceptions",
           "scenario", "feedback", "transfer_scenario", "assessment_rubric")
    for k in req:
        if not item.get(k):
            errors.append(f"Thiếu mục `{k}`")
    for block_name in ("scenario", "transfer_scenario"):
        b = item.get(block_name) or {}
        opts = b.get("options") or []
        ci = b.get("correct_index")
        if not isinstance(opts, list) or len(opts) < 2:
            errors.append(f"`{block_name}` cần ít nhất 2 lựa chọn")
        elif not isinstance(ci, int) or not (0 <= ci < len(opts)):
            errors.append(f"`{block_name}.correct_index` không hợp lệ")
    if item.get("scenario", {}).get("context") == item.get("transfer_scenario", {}).get("context"):
        errors.append("Transfer scenario bị trùng nguyên văn với tình huống chính")
    extra_qs = item.get("extra_questions") or []
    if not isinstance(extra_qs, list):
        errors.append("`extra_questions` phải là danh sách")
    else:
        for idx, eq in enumerate(extra_qs):
            if not isinstance(eq, dict) or not (eq.get("question") or "").strip():
                errors.append(f"Câu hỏi thêm #{idx + 1} thiếu nội dung câu hỏi")
                continue
            opts = eq.get("options") or []
            ci = eq.get("correct_index")
            if not isinstance(opts, list) or len(opts) < 2 or any(not str(o).strip() for o in opts):
                errors.append(f"Câu hỏi thêm #{idx + 1} cần ít nhất 2 lựa chọn hợp lệ")
            elif not isinstance(ci, int) or not (0 <= ci < len(opts)):
                errors.append(f"Câu hỏi thêm #{idx + 1} có đáp án đúng không hợp lệ")
    return {"valid": len(errors) == 0, "errors": errors}


def save_kc_to_kb(kc_code: str, intervention: dict) -> dict:
    """Lưu gói câu hỏi đã được giảng viên chỉnh sửa/bổ sung vào data/kc_knowledge.json."""
    chk = validate_intervention(intervention)
    if not chk["valid"]:
        raise ValueError("; ".join(chk["errors"]))
    kb = _load_kb()
    clean = {
        k: v
        for k, v in intervention.items()
        if k not in ("kc_code", "generation_mode", "validation", "ai_model")
    }
    kb[kc_code] = clean
    with open(KC_KB_PATH, "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)
    saved = dict(clean)
    saved["kc_code"] = kc_code
    saved["generation_mode"] = "teacher_edited"
    saved["validation"] = chk
    return saved


def build_intervention(kc_code: str, kc_meta: dict = None, use_ai: bool = False) -> dict:
    """Tạo gói can thiệp 9 phần có căn cứ (Cost = 0 với bản chuẩn hoá, hoặc tuỳ biến bằng AI nếu bật)."""
    kb = _load_kb()
    meta = kc_meta or {}
    base = dict(kb[kc_code]) if kc_code in kb else _generic_intervention(kc_code, meta)
    base["kc_code"] = kc_code
    base["generation_mode"] = "grounded_verified"
    base["validation"] = validate_intervention(base)

    if use_ai and MODEL_PROVIDER != "fake":
        note(f"intervene: gọi AI tuỳ biến tình huống cho {kc_code}")
        try:
            prompt = (
                f"Dữ liệu pre-class: {kc_code} đạt {meta.get('so_dung_lan_dau','?')}/{meta.get('so_lan_tra_loi_dau','?')} ({meta.get('ti_le_dung_pct','?')}%).\n"
                f"Tài liệu kiến thức chuẩn (JSON mẫu):\n{json.dumps(base, ensure_ascii=False)}\n\n"
                "Hãy tạo một biến thể tình huống thực tế mới mẻ hơn cho cùng KC này, giữ nguyên đúng schema JSON."
            )
            reply = call_model(SYSTEM_INTERVENTION, prompt)
            m = re.search(r"\{.*\}", reply.get("text") or "", re.S)
            if m:
                cand = json.loads(m.group(0))
                cand["kc_code"] = kc_code
                chk = validate_intervention(cand)
                if chk["valid"]:
                    cand["generation_mode"] = "live_ai_validated"
                    cand["ai_model"] = reply.get("model", "")
                    cand["validation"] = chk
                    return cand
                note("intervene validation fallback: " + "; ".join(chk["errors"]))
        except Exception as e:
            note(f"intervene AI fallback: {e}")

    return base


def score_explanation(text: str, rubric: dict) -> dict:
    """Chấm chất lượng giải thích (0–2) dựa theo rubric kiểm chứng được của KC."""
    cleaned = (text or "").strip().lower()
    if len(cleaned) < 8:
        return {"score": 0, "max_score": 2, "note": "Giải thích còn quá ngắn hoặc bỏ trống."}
    groups = (rubric or {}).get("key_concepts") or []
    hits = 0
    for grp in groups[:2]:
        if any(kw.lower() in cleaned for kw in grp):
            hits += 1
    if hits >= 2:
        return {"score": 2, "max_score": 2, "note": "Lập luận đầy đủ, nêu rõ cả bản chất lẫn điều kiện/hệ quả."}
    if hits == 1:
        return {"score": 1, "max_score": 2, "note": "Nêu được 1 khía cạnh hợp lý, có thể làm rõ thêm điều kiện áp dụng."}
    return {"score": 0, "max_score": 2, "note": "Chưa chạm vào ý cốt lõi của rubric — cần đối chiếu lại phần phản hồi."}


def evaluate_submission(
    intervention: dict,
    main_choice: int,
    main_exp: str,
    transfer_choice: int,
    transfer_exp: str,
    extra_choices: list = None,
) -> dict:
    """Chấm một bài làm học viên gồm: Tình huống chính + Giải thích + Transfer Test + Giải thích + câu thêm (nếu có)."""
    sc = intervention["scenario"]
    tr = intervention["transfer_scenario"]
    fb = intervention["feedback"]
    rubric = intervention.get("assessment_rubric") or {}

    main_ok = (int(main_choice) == int(sc["correct_index"]))
    transfer_ok = (int(transfer_choice) == int(tr["correct_index"]))
    exp_eval = score_explanation(main_exp + " " + transfer_exp, rubric)

    extra_qs = intervention.get("extra_questions") or []
    extra_picks = extra_choices or []
    extra_results = []
    for idx, eq in enumerate(extra_qs):
        pick = extra_picks[idx] if idx < len(extra_picks) and extra_picks[idx] is not None else -1
        ok = (int(pick) == int(eq["correct_index"]))
        extra_results.append({
            "question": eq["question"],
            "picked": int(pick),
            "correct": ok,
            "correct_option": eq["options"][int(eq["correct_index"])],
        })

    if main_ok and transfer_ok:
        status = "mastered"
        reasonable = "Bạn chọn đúng ở cả tình huống chính và tình huống mới (Transfer Test)."
        gap = "Không phát hiện lỗ hổng lớn ở hai tình huống này." if exp_eval["score"] >= 1 else "Lựa chọn đúng nhưng phần giải thích lý do còn hơi ngắn."
    elif main_ok and not transfer_ok:
        status = "surface_only"
        reasonable = "Bạn đã chọn đúng ở ví dụ ban đầu."
        gap = "Bạn gặp khó khăn khi chuyển sang bối cảnh mới (Transfer Test) — dấu hiệu chưa vận dụng chắc bản chất."
    elif not main_ok and transfer_ok:
        status = "recovering"
        reasonable = "Bạn đã kịp điều chỉnh và làm đúng ở tình huống Transfer Test."
        gap = "Ở tình huống đầu tiên bạn bị nhầm phương án."
    else:
        status = "persistent_error"
        reasonable = "Bạn đã hoàn thành đủ hai bước để hệ thống nhận diện chỗ đang vướng."
        gap = "Cả hai tình huống đều chưa chính xác — cần xem lại khái niệm cốt lõi."

    return {
        "main_correct": main_ok,
        "transfer_correct": transfer_ok,
        "explanation_score": exp_eval["score"],
        "explanation_note": exp_eval["note"],
        "learning_status": status,
        "extra_results": extra_results,
        "structured_feedback": {
            "reasonable_part": reasonable,
            "gap_part": gap,
            "why_wrong": fb["why_wrong"],
            "relearn": fb["relearn"],
            "when_to_apply": fb["when_to_apply"],
            "main_correct_option": sc["options"][int(sc["correct_index"])],
            "transfer_correct_option": tr["options"][int(tr["correct_index"])],
        },
    }
