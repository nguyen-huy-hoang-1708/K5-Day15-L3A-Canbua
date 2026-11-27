# Tổng hợp bằng chứng pain

> Xong trước **CP3 10:00 Thứ Bảy 28/11**. **Nguồn đạt ngưỡng: đào data BTC** (x/N, %, script chạy lại được, ≥5 ví dụ). Phỏng vấn là nguồn kiểm lại, đang làm.

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☑ | `evidence/data-mining.md` · script `evidence/count_preclass.py` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☐ chưa làm | `evidence/interviews/P1.md`… · câu hỏi: `evidence/interviews/GUIDE-radar.md` |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | ☐ không dùng | — |

## 2. Số chính

- Đào data:
  - Học viên có hoạt động trên bài: Day01 417/436 (95,6%) → Day05 134/436 (30,7%) → Day10 44/436 (10,1%) → Day12 26/436 (6,0%).
  - Ý kiến thức (≥ 20 người) đúng lần đầu < 75%: 7/46 (15,2%); thấp nhất `cot_task_fit` 16/27 (59,3%).
  - Học viên từng nhắn trợ giảng AI: 145/436 (33,3%).
  - Cặp (học viên, video) xem tới cuối: 1676/3900 (43,0%).
- Phỏng vấn: __/3 người gặp · số lần / tháng: P1 __, P2 __, P3 __ · mỗi lần mất __–__ phút *(chưa làm)*

| | Vai | Gặp pain? | Số lần / 1 tháng qua | Lần gần nhất mất | Đang xoay xở bằng |
|---|---|---|---|---|---|
| P1 | | | | | |
| P2 | | | | | |
| P3 | | | | | |

## 3. ≥5 ví dụ cụ thể từ data (mã dòng / mã video, không có tên học viên)

Nguồn đạt ngưỡng là **đào data** nên "trích dẫn" ở đây là dòng data cụ thể, kiểm lại được bằng script:

1. `answers.csv` **A00515**, **A00295**, **A00833**, **A00616**, **A01153** — 5 lần trả lời **sai ngay lần đầu** ở ý `cot_task_fit` (Day04, cả ý: 16/27 đúng = 59,3%). In lại: `python evidence/count_preclass.py data-btc/preclass` mục [7].
2. Ý `chatbot_is_app_around_model` (Day01, ý nhiều người trả lời nhất của ngày đầu): 25/41 đúng lần đầu (61,0%) — gần 4/10 người hiểu sai "chatbot là ứng dụng bọc quanh model".
3. Video **`d01-r1-v01`** (video mở đầu Day01): 187 người xem, chỉ 66/187 còn ở khoảng cuối; 22% người xem tua tới qua khoảng 1:45 (`data/preclass_video_stats.json`).
4. **Day12**: 26/436 người có hoạt động trên bài pre-class (6,0%), so với Day01 417/436 (95,6%) — giảng viên Day12 gần như không có số pre-class để dựa vào.
5. **Day09**: không ý kiến thức nào có từ 10 người trả lời trở lên (nhiều nhất 6 người, `llm_judge_calibration`) → Radar trả "Chưa đủ dữ liệu" thay vì đoán (câu thử K03).

*(Trích dẫn nguyên văn của giảng viên / lab coach sẽ thêm vào đây sau phỏng vấn — `evidence/interviews/P1.md`…)*

## 4. Các nguồn có khớp nhau không

Data nói: có ý kiến thức hổng rõ và đếm được; pre-class tụt mạnh theo ngày. Người dùng nói: __ *(chưa phỏng vấn)*. Data không cho biết giảng viên có đang thấy chỗ hổng này không — đây là điều phỏng vấn phải trả lời.

## 5. Kết luận

Giả thuyết ở `evidence/hypothesis.md`: **đúng một nửa (phần data)** — 7 ý < 75% (đạt điều kiện "≥ 5 ý"). Phần giảng viên có gặp pain hay không: **chưa biết**, cần ≥3 phỏng vấn trước CP3.

## Lịch hẹn (chỉ ghi vai và giờ)

| Vai | Giờ hẹn | Đã xong? |
|---|---|---|
| Giảng viên L3 | __ | ☐ |
| Lab coach L3 | __ | ☐ |
| Lab coach / key coach | __ | ☐ |
