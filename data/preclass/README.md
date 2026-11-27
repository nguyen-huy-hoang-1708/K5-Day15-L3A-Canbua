# Data pack — trang pre-class của khoá (AI20K Level 3-4, khoá 5)

> `README.md` → `01-challenge-brief.md` → `tracks/` → **`data/preclass/`** → `02-guide.md`
> Liên quan nhất tới [Track A](../../tracks/track-a-edtech.md): hướng A1 (tutor) và A4 (lớp học kiểu mới); hướng khác dùng được nếu bài toán chạm tới việc học trước buổi.

Đây là nhật ký **hành vi** của học viên khoá mình trên trang pre-class ([preclass-online.com](https://preclass-online.com)): mở bài, xem video, tua, trả lời câu hỏi, làm mini lab, nhắn trợ giảng AI và bạn học AI. Mỗi file là một bảng CSV, mở thẳng bằng Excel, Google Sheets hoặc pandas.

**Đào data là một cách tìm bằng chứng pain**, ngang với phỏng vấn và khảo sát. Data cho nhóm **con số hành vi thật** (bao nhiêu người, bao nhiêu lần, bỏ ở đâu); phỏng vấn và khảo sát cho biết **vì sao** và kiểm lại xem điều đào được có đúng là chỗ đau không. Cách mạnh nhất: **đào data ra insight → hỏi người dùng để kiểm lại** (hoặc ngược lại: nghe người dùng kể → vào data đếm xem có bao nhiêu người như vậy). Cách làm: [02-guide.md bước 1.2](../../02-guide.md#b1-2).

**Data không kèm gợi ý hay đáp án.** File này chỉ mô tả dữ liệu. Đào gì, đếm thế nào, kết luận gì là việc của nhóm — và phải ghi cách đếm để người khác kiểm lại được.

---

## Quy mô

| | |
|---|---|
| Khoảng thời gian | 05/11/2026 → 25/11/2026 |
| Ngày học có dữ liệu | Day01 → Day13 |
| Học viên | 721 tài khoản, **436 người có hoạt động** |
| Câu chữ học viên viết | **Không có.** Chỉ có độ dài (số ký tự) |

## Đã bảo vệ danh tính thế nào

- Không có tên, email, số điện thoại, IP, mã thiết bị.
- **Mọi mã đã được thay mới**: học viên `L0001…`, lượt chat `C00001…`, lần trả lời `A00001…`, buổi `S0001…`, gợi ý `G01…`, phiên bản hướng dẫn AI `P1…`, phiên bản bài giảng `V1…`. Thứ tự xáo ngẫu nhiên, **không có bảng đối chiếu** về mã gốc.
- Chỉ giữ học viên; tài khoản giảng viên, lab coach, kiểm thử đã bị bỏ. Ngày tạo tài khoản chỉ giữ ngày.
- Đã bỏ trường kỹ thuật nội bộ (trace, cache, phiên bản phần mềm). Tên model ghi chung là `model_chinh` / `fallback`.
- Một số trạng thái chấm nhạy cảm (nhãn máy tự gắn, không kiểm lại được) đã được gộp vào `bo_qua` trong `answers.csv`.

**Luật dùng:** không cố đoán ai là ai · không xếp hạng học viên · trong repo nhóm chỉ để số đã tổng hợp và vài dòng trích làm ví dụ, không đăng lại nguyên file ở nơi khác.

## Các file

| File | Số dòng | Một dòng là |
|---|---:|---|
| `learners.csv` | 721 | một học viên (`hv`, ngày tạo tài khoản) |
| `events.csv` | 107.709 | một việc học viên làm, hoặc AI làm cho học viên |
| `class_events.csv` | 849 | một việc chung của lớp: bộ điều phối lớp học AI quyết định có cho bạn học AI xen vào không |
| `answers.csv` | 3.776 | một lần học viên trả lời câu hỏi, làm bước thực hành, tự giải thích, hoặc nhắn AI (được chấm theo rubric) |
| `chat.csv` | 1.260 | một lượt học viên nhắn AI và AI trả lời (độ dài, AI nào, kênh nào) |
| `completed_items.csv` | 2.472 | một mục bài học học viên đã xong |
| `rewards.csv` | 228 | một lần học viên được thưởng điểm vì hành vi học tốt |
| `column_dictionary.csv` | — | nghĩa từng cột của mọi file |
| `event_types.csv` | — | nghĩa từng loại việc trong `events.csv` / `class_events.csv`, số dòng mỗi loại, khoá có trong cột `data` |


## Nối các file

- Cột `hv` có ở mọi file (trừ `class_events.csv`) → `learners.csv`.
- Một lượt nhắn AI: `chat.csv` `id` = `answers.csv` `ref` (dòng `nguon` = `chat`) = `events.csv` `ref_id` (dòng `type` = `chat_sent` / `agent_replied`).
- Một lần trả lời: `answers.csv` `id` = `events.csv` `ref_id` (dòng `type` = `answer_submitted`) = `rewards.csv` `evidence_id`.
- Theo bài: `lesson_id` (`program-dayNN:tên-bài`). Theo ý kiến thức: `kc_code`. Câu hỏi dưới video: xem cột `transcript` (`DayNN/...`) vì `lesson_id` thường trống.
- Chi tiết mỗi việc nằm trong cột `data` (JSON) — khoá có gì xem `event_types.csv`.

## Lưu ý khi đếm

- **Giờ là UTC.** Giờ Việt Nam = UTC + 7.
- **Ô trống ≠ sai.** `True`/`False` là đúng/sai; trống là không áp dụng.
- **Chọn mẫu số cho đúng.** 721 tài khoản nhưng chỉ 436 người có hoạt động.
- **Lần đầu và làm lại:** `answers.csv` giữ mọi lần trả lời; đo hiểu bài thường lấy `lan_thu` = 1.
- **Chế độ học** (`learning_mode`: `maic` = học cùng lớp AI có bạn học AI, `tutor` = chỉ trợ giảng AI) và `prompt_version` **chỉ có từ 25/11/2026** — rất ít dòng, đừng so `maic` với `tutor` trên bộ này.
- **Phiếu đánh giá cuối ngày** đã bỏ (nhóm lớp này chỉ có 1 phiếu, dễ nhận diện).
- Mỗi loại dữ liệu bắt đầu ghi từ ngày khác nhau; ô trống trước ngày đó không có nghĩa là học viên không làm.

---

Khi đưa số từ data vào bằng chứng: ghi **đếm gì · trên bao nhiêu dòng / người · lọc thế nào · x/N và %**, kèm script hoặc công thức để người khác chạy lại được. Cách viết: [02-guide.md](../../02-guide.md).
