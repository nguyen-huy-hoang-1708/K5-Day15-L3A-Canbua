# Đào data — cách đếm và kết quả

> Repo chỉ chứa số đã tổng hợp và mã dòng ví dụ — không chép lại nguyên file data.

## 1. Cách đếm

- Data dùng: `data/preclass/` do BTC cấp — `events.csv`, `answers.csv`, `chat.csv`; 05/11/2026 → 25/11/2026, Day01 → Day13.
- Đếm gì · trên tập nào · lọc gì:
  1. Học viên có hoạt động trên bài từng ngày: số `hv` riêng có ≥1 dòng `actor = learner` với `lesson_id` chứa `dayNN`.
  2. Xem hết video: cặp (`hv`, `video`) có `video_ended` trên cặp có `video_opened`.
  3. Hiểu bài theo ý kiến thức: `answers.csv`, chỉ `lan_thu = 1` và `was_correct` là `True`/`False` (bỏ ô trống); gom theo `kc_code`; chỉ giữ KC có ≥20 học viên trả lời.
  4. Dùng trợ giảng AI: số `hv` riêng trong `chat.csv`.
  5. Mini lab: `lab_completed` có `skipped = true` trên tổng `lab_completed`.
- **Mẫu số:** 436 học viên có hoạt động (không dùng 721 tài khoản); với KC là số lần trả lời đầu của KC đó.
- Script: `python evidence/count_preclass.py data-btc/preclass` (chỉ dùng thư viện chuẩn, không in mã học viên).
- Ghi chú trung thực: nhóm đã đếm thử vài số trước khi viết mục này, sau đó mới viết script cố định. Script trên là cách đếm chính thức.

## 2. Đọc trước, đếm sau

Đã đọc 3 dòng đầu mỗi file, `column_dictionary.csv` và `event_types.csv`. Các *kiểu* hành vi thấy được:
- Học viên mở video, tua, rời tab (`app_visibility_changed` là loại sự kiện nhiều nhất, 30.948 dòng), trả lời câu hỏi giữa video.
- Hỏi trợ giảng AI ngay dưới video (`video_question`), trả lời bạn học AI (`video_discussion_reply`).
- Làm mini lab, có thể bấm bỏ qua.
- Tài khoản giảng viên đã bị bỏ khỏi data → **không thấy được giảng viên dùng kết quả pre-class thế nào**.

## 3. Kết quả

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| Học viên có hoạt động trên bài Day01 | 417/436 | 95,6% | |
| … Day05 | 134/436 | 30,7% | |
| … Day10 | 44/436 | 10,1% | |
| … Day12 | 26/436 | 6,0% | Day13: 50/436 (11,5%) |
| Cặp (học viên, video) xem tới cuối | 1676/3900 | 43,0% | |
| Lần đầu trả lời đúng (mọi KC) | 2054/2478 | 82,9% | |
| KC đúng lần đầu < 75% (trong KC có ≥20 người) | 7/46 | 15,2% | |
| `cot_task_fit` (Day04 prompt engineering) đúng lần đầu | 16/27 | 59,3% | 27 người |
| `chatbot_is_app_around_model` (Day01) | 25/41 | 61,0% | 41 người |
| `complete_ai_problem_statement` (Day02) | 15/23 | 65,2% | 23 người |
| `system_prompt_contract` (Day04) | 18/27 | 66,7% | 27 người |
| Học viên từng nhắn AI | 145/436 | 33,3% | 1.260 lượt chat |
| Mini lab bấm bỏ qua | 102/453 | 22,5% | trên số `lab_completed` |

## 4. ≥5 ví dụ cụ thể

Lần trả lời đầu **sai** ở KC `cot_task_fit` (mã dòng `answers.csv`):
1. A00515
2. A00295
3. A00833
4. A00616
5. A01153

## 5. Giới hạn của data

- Data cho biết học viên **làm gì**, không cho biết **vì sao** bỏ pre-class hay trả lời sai (không có chữ học viên viết).
- Không có dữ liệu phía giảng viên → chưa biết giảng viên có đang xem kết quả pre-class không, mất bao lâu, có cần hay không.
- Số người theo KC nhỏ (23–41 người) → % dao động lớn; mỗi loại dữ liệu bắt đầu ghi từ ngày khác nhau.
- Mẫu lệch về phía học viên còn học pre-class (người bỏ thì không có dòng).

→ Kiểm lại bằng: phỏng vấn ≥3 giảng viên / lab coach L3 — "Lần gần nhất chuẩn bị buổi, bạn biết lớp hổng ý nào bằng cách nào? Mất bao lâu? Có từng thấy kết quả pre-class không?"
