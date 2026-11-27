# Chi phí khi dùng thật

> Số chép từ `cost/simulate-1-summary.md` (do `python run.py simulate` sinh ra, không điền tay).

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu — giảng viên LEC (40%, 6 phiên / tháng, 2 lượt hỏi / phiên), lab coach (50%, 4 phiên, 1 lượt), ban đào tạo (10%, 20 phiên, 3 lượt). Nguồn: số buổi / giảng viên từ README `data/training-ops` (BTC cấp, giả lập theo bảng thật); phần còn lại *(tự ước tính)*, cần kiểm bằng phỏng vấn.
- **Số người dùng thật** 3 kịch bản: thấp 22 · cơ sở 50 · cao 92. Nguồn: README `training-ops` — 22 giảng viên, 8 hỗ trợ, 62 lab coach mỗi khoá; cơ sở *(tự ước tính)*.
- **Giá** 5 mức model: Claude Haiku 5.5 / Sonnet 5.5 / Opus 5.5 (bảng giá Anthropic) · Cloudflare Workers AI Mistral Small 3.1 24B / Llama 3.3 70B (developers.cloudflare.com/workers-ai/platform/pricing, xem 27/11/2026).
- **Tỉ lệ đạt** dùng để tính: 23/25 (92%) — lượt `run-2@20261127-162833` (lượt 2).
- Đo token trên model `@cf/mistralai/mistral-small-3.1-24b-instruct`, tính giá cả 5 model. Bộ tách token mỗi hãng khác nhau nên số của các model khác là ước lượng.

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID simulate-1@20261127-163014 · 50 phiên · seed 42 · 0 phiên lỗi

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp (22) | / tháng — cơ sở (50) | / tháng — cao (92) | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | $0.00029 | $0.00031 | $0.0397 | $0.0903 | $0.1662 | $0.0018 |
| claude-sonnet-5-5 | $0.0057 | $0.0062 | $0.7948 | $1.81 | $3.32 | $0.0361 |
| claude-opus-5-5 | $0.0114 | $0.0124 | $1.59 | $3.61 | $6.65 | $0.0723 |
| @cf/mistralai/mistral-small-3.1-24b-instruct (đang dùng) | $0.00077 | $0.00084 | $0.1070 | $0.2432 | $0.4476 | $0.0049 |
| @cf/meta/llama-3.3-70b-instruct-fp8-fast | $0.00099 | $0.0011 | $0.1377 | $0.3131 | $0.5760 | $0.0063 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt (92%).

Token / phiên: giảng viên 2623 vào · 275 ra; lab coach 1323 · 123; ban đào tạo 1488 · 162. Chỉ khoảng một nửa lượt hỏi phải gọi model (câu từ chối, hỏi lại, "chưa đủ dữ liệu" trả lời bằng code).

**Gói miễn phí Cloudflare** (10.000 neuron / ngày) đủ cho quy mô này: cả tháng ở kịch bản cao tốn $0,45 theo giá trả phí, tức khoảng 1.360 neuron / ngày nếu quy đổi theo $0,011 / 1.000 neuron *(ước lượng từ bảng giá)*.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): chưa có số từ phỏng vấn. Giả định *(tự ước tính)*: Radar giúp giảng viên tiết kiệm ≥ 5 phút chuẩn bị mỗi buổi × 6 buổi = 30 phút / tháng.
- Chi phí / người / tháng (cơ sở, Mistral Small trên Cloudflare): **$0,0049** (Claude Haiku 5.5: $0,0018; Claude Opus 5.5: $0,072).
- **Kết luận một dòng:** đáng làm — chi phí model dưới 1 cent / người / tháng, nhỏ hơn rất nhiều so với giá trị chỉ vài phút của giảng viên; rủi ro thật nằm ở chất lượng lời giải thích (xem `eval/report.md`), không nằm ở chi phí, nên có thể chọn model mạnh hơn (Opus 5.5: $3,61 / tháng ở cơ sở) nếu cần chất lượng.

## 4. Độ nhạy

- Đổi model là cần gạt lớn nhất: từ Haiku 5.5 đến Opus 5.5 chênh ~40 lần, nhưng tổng vẫn dưới $7 / tháng ở kịch bản cao.
- Cache theo ngày ở giao diện web (`web.py`): Radar của một ngày chỉ gọi model lần đầu, các lần mở lại 0 token — với 13 ngày dữ liệu, cả khoá tốn tối đa 13 lượt gọi cho phần chọn ngày (chưa tính câu hỏi tự do). Mô phỏng ở mục 2 KHÔNG tính cache (đi qua `answer()`), nên là mức trên.
- Input chiếm phần lớn token (~1.300 / lượt gọi, chủ yếu là prompt hệ thống + bảng KC). Cache prompt hệ thống hoặc chỉ gửi KC đủ ngưỡng sẽ giảm thêm.
- Chi phí ngoài model: dựng lại `data/preclass_day_stats.json` mỗi ngày (vài giây chạy script) — không đáng kể; giờ công người duyệt: không cần, vì Radar không tác động ra ngoài.
