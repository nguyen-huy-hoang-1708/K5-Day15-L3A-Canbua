# Khai báo dùng AI

> Luật của đề: ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử (`codebase/agent.py`, `tools.py`, `ai.py`) | Claude Code | Viết workflow, luật chặn, bước kiểm số, nhánh gọi model | Chạy `python run.py` với các câu ở `eval/benchmark.csv`; đọc lại luật chặn | __ |
| Prompt / thiết kế lời gọi mô hình | Claude Code | Viết `SYSTEM` trong `agent.py` (model trả JSON, chỉ dùng số được đưa) | Kiểm output thật sau khi nối model | __ |
| Đào data (`evidence/count_preclass.py`, `data/build_aggregate.py`) | Claude Code | Viết script đếm, chọn mẫu số | Chạy lại script, đối chiếu vài số bằng Excel/Sheets: kiểm tay __ số, khớp __ | __ |
| Rà câu hỏi phỏng vấn (`evidence/interviews/GUIDE-radar.md`) | Claude Code | Gợi ý câu hỏi theo kiểu "lần gần nhất" | Rà câu dẫn dắt | __ |
| Viết câu thử (`eval/benchmark.csv`, `eval/checks.json`) | Claude Code | Viết 25 câu; đáp án câu `data_that` lấy từ số tổng hợp | Mỗi câu có `source`; kiểm đáp án bằng `data/preclass_day_stats.json` | __ |
| Chấm cột `pass` | Không dùng LLM — chấm bằng code (`eval/grade_run.py`) | — | Người thứ hai chấm tay 5 output, ghi ở `eval/README.md` mục 3 | __ |
| Văn bản (`spec.md`, `canvas.md`, `evidence/*.md`, `data/DATA_CARD.md`) | Claude Code | Bản nháp từ data | Nhóm sửa, điền phần phỏng vấn | __ |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy.
