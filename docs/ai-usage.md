# Khai báo dùng AI

> Luật của đề: ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử (`codebase/agent.py`, `tools.py`, `ai.py`) | Claude Code | Viết workflow, luật chặn, bước kiểm số, nhánh gọi model | Chạy `python run.py` với các câu ở `eval/benchmark.csv`; đọc lại luật chặn | Đỗ Hoàng Phúc |
| Prompt / thiết kế lời gọi mô hình | Claude Code | Viết `SYSTEM` trong `agent.py` (model trả JSON, chỉ dùng số được đưa) | Kiểm output thật sau khi nối model | Đỗ Hoàng Phúc |
| Đào data (`evidence/count_preclass.py`, `data/build_aggregate.py`) | Claude Code | Viết script đếm, chọn mẫu số | Chạy lại script; đối chiếu 5 số chính (417/436, 26/436, 16/27, 25/41, 1676/3900) giữa hai script viết riêng (`count_preclass.py`, `build_aggregate.py`): khớp 5/5. Kiểm tay bằng Excel/Sheets: chưa làm | Nguyễn Huy Hoàng |
| Rà câu hỏi phỏng vấn (`evidence/interviews/GUIDE-radar.md`) | Claude Code | Gợi ý câu hỏi theo kiểu "lần gần nhất" | Rà câu dẫn dắt | Lê Hoàng Sơn |
| Viết câu thử (`eval/benchmark.csv`, `eval/checks.json`) | Claude Code | Viết 25 câu; đáp án câu `data_that` lấy từ số tổng hợp | Mỗi câu có `source`; kiểm đáp án bằng `data/preclass_day_stats.json` | Phạm Tuấn Anh |
| Chấm cột `pass` | Không dùng LLM — chấm bằng code (`eval/grade_run.py`) | — | Người thứ hai chấm tay 5 output, ghi ở `eval/README.md` mục 3 | Phạm Tuấn Anh |
| Bảng thuật ngữ (`data/glossary.json`) | Claude Code | Viết nghĩa 47 cụm thuật ngữ từ tên ý kiến thức | **Cần giảng viên duyệt** trước khi dùng thật | Đỗ Hoàng Phúc |
| Giao diện web (`web.py`, `web/index.html`) | Claude Code | Viết trang, biểu đồ, cache, phiếu chuẩn bị | Thử trên trình duyệt: Day 1, 4, 9, câu tấn công | Lê Hoàng Sơn |
| Trò chơi Mê cung (`game.py`, `web/game.html`) và 30 câu hỏi nháp | Claude Code | Viết logic trò chơi, đồ hoạ, soạn câu hỏi | Thử nhiều người chơi trên trình duyệt; **câu hỏi cần giảng viên duyệt** | Đỗ Hoàng Phúc |
| Văn bản (`spec.md`, `canvas.md`, `evidence/*.md`, `data/DATA_CARD.md`) | Claude Code | Bản nháp từ data | Nhóm sửa, điền phần phỏng vấn | Nguyễn Huy Hoàng |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy.
