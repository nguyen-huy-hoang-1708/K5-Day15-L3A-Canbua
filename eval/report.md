# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Số lấy từ `python eval/grade_run.py eval/run-N.csv` (chấm bằng code, điền cột `pass`) rồi `python run.py score eval/run-N.csv`.
> Cùng bộ 25 câu thử, cùng cách chấm (5 metric ở `eval/metric_spec.yaml`), cùng model `@cf/mistralai/mistral-small-3.1-24b-instruct` (Cloudflare Workers AI).

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | run-1@20261127-162546 | 15/25 | 60% | 3/12 | 7/8 | 5/5 | chưa đạt (cần ≥ 22/25) |
| 2 | run-2@20261127-162833 | 23/25 | 92% | 10/12 | 8/8 | 5/5 | **đạt** (≥ 22/25 · tu_choi 5/5 · 0 câu sai số liệu) |
| 3 *(thêm, sau lượt 2)* | run-3@20261127-165741 | 25/25 | 100% | 12/12 | 8/8 | 5/5 | đạt |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

Ghi chú trung thực: lượt 1 lúc đầu được chấm 24/25 theo 4 metric. Đọc output thấy lời giải thích của AI giống hệt nhau ở mọi câu, nên nhóm thêm metric `ly_do_cu_the` (16:30, trước CP2) và chấm lại lượt 1 → 15/25. Không sửa câu thử, `expected` hay output.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Lý do chung chung, y hệt nhau ("Tỉ lệ đúng lần đầu thấp và nhiều người trả lời") | 10 câu trượt (11/11 câu có lời giải thích bị lỗi này) | B01–B07, B09, B10, K08 |
| Bỏ sót ý đang hổng | 1 | B04 (bỏ `agentic_fit_scoring_decision`, 73,3%) |
| Hiểu sai tên ý kiến thức *(không làm trượt metric, đọc tay)* | ≥ 4 | B01, B09, B12: `cot_task_fit` thành "phù hợp công cụ"; B02: `complete_ai_problem_statement` thành "hoàn thiện câu hỏi AI" |
| Nhận xét nhắc ý không được chọn / bịa *(đọc tay)* | 2 | B07 nhắc 2 ý không có trong danh sách chọn; B10 nhắc "kiến trúc phần cứng" |
| Model không trả JSON hợp lệ → dùng dự phòng | 1 | B11 (vẫn đạt vì câu này chỉ hỏi số người) |

**≥3 lỗi cụ thể:**

| Câu | Input | Output (trích) | Vì sao sai |
|---|---|---|---|
| B04 | Ngày 3 cần giảng kỹ phần nào? | Chỉ liệt kê `react_reasoning_acting_pattern`, `trace_based_agent_evaluation` | Day03 có 3 ý dưới 75%; giảng viên không biết `agentic_fit_scoring_decision` (33/45) cũng đang hổng |
| B01 | Day 4 lớp đang hổng ý nào? | `cot_task_fit` — Gợi ý: "Nhấn mạnh về việc phù hợp giữa công cụ và nhiệm vụ" | CoT là chain-of-thought; gợi ý dẫn giảng viên giảng sai chủ đề |
| B02 | Mai mình dạy buổi Day 2… | Cả 3 ý: "Vì sao: Tỉ lệ đúng lần đầu thấp và nhiều người trả lời." | Không cho biết ý nào nặng hơn, giảng viên không ưu tiên được |

## 3. Một lần cải tiến

- **Nhắm vào nhóm lỗi:** "chọn và giải thích ý hổng" (lý do chung chung + bỏ sót + hiểu sai tên ý). Đau nhất với giảng viên vì đây là phần duy nhất AI quyết định; sai thì giảng viên nhấn nhầm hoặc bỏ sót ý trong buổi.
- **Đã sửa** (`codebase/agent.py`):
  1. Prompt: có ≤ 3 ý dưới ngưỡng thì phải chọn tất cả; thêm trường `y_nghia` giải nghĩa mã ý (kèm bảng viết tắt cot, react, eval, rag; không chắc thì ghi "Chưa chắc nghĩa — xem slide bài"); cấm câu lý do chung, lý do các ý phải khác nhau; nhận xét chỉ nói về ý đã chọn.
  2. Code tính sẵn số phụ cho mỗi ý (hạng trong ngày, chênh so với trung bình ngày, số câu sai lần đầu) để model có cái riêng mà nói; các số này được thêm vào danh sách số hợp lệ của bước kiểm số.
  3. Code chặn bỏ sót: model chọn thiếu ý hổng (khi có ≤ 3 ý) → code thêm ý còn thiếu, không kèm lời giải thích, có ghi trace. Ở lượt 2 chặn này **không phải kích hoạt lần nào** (model đã tự chọn đủ).
- **Kết quả:** nhóm lỗi đó 11 câu trượt → 2 câu trượt · tổng 60% → 92% · thuong 3/12 → 10/12.
- **Câu tệ đi sau khi sửa:** không có câu nào đạt ở lượt 1 mà trượt ở lượt 2.

## 3b. Lượt thêm (lượt 3) — bảng thuật ngữ

Không tính là "một lần cải tiến" chính của mục 3 (đã chốt ở lượt 2); ghi thêm cho trung thực.

- **Nhắm vào:** lỗi dịch sai thuật ngữ còn lại sau lượt 2 (mục 4 bên dưới).
- **Đã sửa:** thêm `data/glossary.json` (47 cụm thuật ngữ, nhóm viết từ tên ý kiến thức — **chưa được giảng viên duyệt**, `da_duyet: false`) và công cụ `get_glossary`; prompt chỉ nhận các cụm có trong ý đang hổng của ngày đó và phải dùng đúng nghĩa trong bảng.
- **Kết quả:** 23/25 → 25/25 (B02, B06 hết lặp lý do). Đếm tay trên toàn bộ output: "đại lý" 2 lần (lượt 2) → 0 (lượt 3); ReAct, recall@k, "tác tử AI" được giải nghĩa đúng. Token vào tăng nhẹ: tổng 26.612 → 27.444 (+3%).
- **Câu tệ đi:** không có.
- Mô phỏng chi phí (`cost/simulate-1.csv`) vẫn dùng tỉ lệ đạt của lượt 2 (92%) — giữ nguyên, là mức thận trọng hơn.

## 4. Còn lại

- **Lý do vẫn lặp ở 2 câu** (B02: cả 3 ý "Có nhiều người trả lời sai lần đầu"; B06: ý 2 và 3 giống nhau). Nguy hiểm thấp: số x/N vẫn đúng, giảng viên vẫn so được bằng số.
- **Dịch sai thuật ngữ** (lượt 2, đọc tay): "agent" → "đại lý" (B02), ReAct → "suy luận của chatbot" (B04), recall@k → "khả năng nhớ ở vị trí k" (B06). **Đã xử lý ở lượt 3** bằng bảng thuật ngữ; bảng vẫn cần giảng viên duyệt, và ý có thuật ngữ ngoài bảng vẫn có thể bị dịch sai.
- **Lý do vẫn thiên về thứ hạng** ("thấp nhất / thấp thứ hai trong ngày") — đúng nhưng chưa nói vì sao học viên sai; data không có nội dung câu trả lời nên chưa làm được hơn.
- **Luật chặn ngoài phạm vi là so khớp từ khoá** → câu diễn đạt lạ có thể lọt; model vẫn chỉ nhận số tổng hợp nên không lộ cá nhân được.
- **Nếu có thêm 1 tuần:** phỏng vấn giảng viên để lấy câu thử `nguoi_dung`; bảng thuật ngữ đã duyệt; tách số theo lớp khi có data lớp; thử model 70B so chất lượng / chi phí.
