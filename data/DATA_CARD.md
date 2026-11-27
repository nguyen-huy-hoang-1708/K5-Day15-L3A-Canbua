# Data card — dữ liệu bản chạy thử dùng

> Không commit nguyên file data BTC cấp. Repo chỉ có file số tổng hợp dưới đây + script dựng lại.

## Dataset 1 · Số tổng hợp pre-class theo ngày học và ý kiến thức — `data/preclass_day_stats.json`

| | |
|---|---|
| Dùng để làm gì | Nguồn cho công cụ `get_day_stats`, `list_days` (`codebase/tools.py`) · nguồn đáp án cho câu thử `data_that` (`eval/benchmark.csv`) · nguồn để `eval/grade_run.py` kiểm số |
| Từ đâu | Data BTC cấp `data/preclass/` của repo đề: `events.csv`, `answers.csv`, `chat.csv` (AI20K khoá 5) |
| Xử lý những bước gì | Script `data/build_aggregate.py` (chỉ thư viện chuẩn). Lọc: sự kiện `actor = learner`; câu trả lời `lan_thu = 1` và `was_correct` là True/False. Gom: theo ngày học (số trong `lesson_id`) và `kc_code`. Ẩn danh: chỉ giữ số đếm, **không giữ mã học viên, mã dòng, thời gian từng lần**. Chạy lại: `python data/build_aggregate.py data-btc/preclass` |
| Số dòng / số đoạn | 13 ngày học · 160 cặp (ngày, KC) · 1 file JSON ~35 KB |
| Phiên bản / ngày lấy | Data BTC 05/11/2026 → 25/11/2026 (Day01–Day13) · dựng ngày 27/11/2026 |
| Nhãn | thật (số tổng hợp từ log thật, không sinh thêm) |
| Giới hạn | Không tách lớp L3A/L3B (data không có cột lớp). Chỉ đếm người đã làm câu hỏi pre-class — người bỏ không có dòng. Số người theo KC nhỏ (Day09–13: mọi KC < 10 người). `answers.csv` đã gộp vài trạng thái chấm nhạy cảm vào `bo_qua` (README data BTC). Không có nội dung bài giảng dạng chữ → AI chỉ biết tên KC và tên bài |

**Ngưỡng dùng trong bản chạy thử** (đặt trước khi chạy, trong `codebase/agent.py`): KC cần ≥ 10 người trả lời lần đầu mới được kết luận (G10); "đang hổng" = đúng lần đầu < 75% (75% thấp hơn rõ mức chung 82,9%, xem `evidence/data-mining.md`).

## Dataset 2 · Bộ câu thử — `eval/benchmark.csv` + luật chấm `eval/checks.json`

| | |
|---|---|
| Dùng để làm gì | Chạy `python run.py eval`, chấm bằng `python eval/grade_run.py` |
| Từ đâu | 15 câu `data_that` (hỏi về một ngày có thật, đáp án lấy từ Dataset 1) · 10 câu `tu_viet` (câu thiếu thông tin, ngoài phạm vi, tấn công — nhóm tự viết) |
| Số dòng | 25 câu: thuong 12 · kho 8 · tu_choi 5 (2 câu tấn công: T02, T03) |
| Nhãn | thật (đáp án từ data) / tự viết. Không có câu từ phỏng vấn (`nguoi_dung`) — chưa phỏng vấn |
| Giới hạn | Câu hỏi do nhóm viết, chưa lấy từ lời giảng viên thật → sau phỏng vấn nên thêm câu `nguoi_dung` |

## Không dùng

`data/training-ops/` (giả lập) chỉ dùng để ước quy mô người dùng ở `cost/personas.yaml`, không làm nguồn cho bản chạy thử và không làm bằng chứng pain.
