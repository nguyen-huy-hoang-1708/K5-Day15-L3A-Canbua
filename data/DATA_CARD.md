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

## Dataset 1b · Số tổng hợp xem video — `data/preclass_video_stats.json`

| | |
|---|---|
| Dùng để làm gì | Thẻ "Video của ngày: học viên bỏ ngang và tua qua ở đâu" trên giao diện web (`web.py`, `/api/videos`) · bằng chứng ở `evidence/data-mining.md` mục 3. **Không** đưa vào model, không dùng trong `answer()` / eval |
| Từ đâu | `events.csv` của data BTC: `video_segments_flushed`, `video_seeked`, `video_ended`, `quiz_item_opened` |
| Xử lý những bước gì | Script `data/build_video_stats.py`: gộp đoạn đã xem của từng học viên theo video → đếm theo khoảng 15 giây: số người còn xem (≥ 50% khoảng), số người tua tới ≥ 15 giây qua khoảng đó; vị trí câu hỏi giữa video. Chỉ giữ số đếm, không giữ mã học viên. Chạy lại: `python data/build_video_stats.py data-btc/preclass` |
| Số dòng / số đoạn | 79 video (61 video có ≥ 10 người xem) · ~37 KB |
| Nhãn | thật (số tổng hợp từ log thật) |
| Giới hạn | "Đã xem" theo log trình phát, có thể lệch khi mất mạng / đổi tab; khoảng cuối video thường thấp vì người xem tắt khi gần hết — giao diện không tính khoảng cuối khi tìm "rơi mạnh nhất"; không biết vì sao người học bỏ ngang |

## Dataset 1c · Bảng thuật ngữ — `data/glossary.json`

| | |
|---|---|
| Dùng để làm gì | Công cụ `get_glossary`: đưa nghĩa các cụm thuật ngữ có trong mã ý kiến thức đang hổng vào prompt, để AI giải nghĩa đúng (từ lượt 3) |
| Từ đâu | Nhóm tự viết từ tên ý kiến thức trong Dataset 1 (47 cụm) |
| Nhãn | tự viết — **chưa được giảng viên duyệt** (`da_duyet: false`) |
| Giới hạn | Chỉ phủ các cụm nhóm nghĩ ra; cụm ngoài bảng vẫn có thể bị dịch sai. Cần giảng viên sửa / duyệt trước khi dùng thật |

## Dataset 1d · Ngân hàng câu hỏi trò chơi — `data/game_questions.json`

| | |
|---|---|
| Dùng để làm gì | Câu trắc nghiệm ở cửa và khi đấu trong trò chơi Mê cung (`game.py`). Ưu tiên câu thuộc ý lớp đang hổng (tỉ lệ đúng lấy từ Dataset 1) |
| Từ đâu | Nhóm tự soạn 30 câu theo tên ý kiến thức của khoá — **chưa được giảng viên duyệt** (`da_duyet: false`) |
| Xử lý | Đáp án không gửi xuống trình duyệt; thứ tự lựa chọn xáo mỗi lần hỏi |
| Giới hạn | Không có nội dung bài giảng trong data → câu hỏi có thể lệch với cách giảng của khoá; cần giảng viên sửa / thay |

**Dữ liệu trò chơi sinh ra khi chơi** — `.game/accounts.json` (tên đăng nhập, họ tên hiển thị, vai trò, mật khẩu đã băm PBKDF2 + salt; không lưu mật khẩu gốc) và `.game/profiles.json` (điểm, lịch sử ván theo tài khoản) — là dữ liệu cá nhân mới → đã đưa vào `.gitignore`, không commit, không gửi vào model.

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
