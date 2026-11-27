# Hồ sơ đánh giá — một trang

> Điền ở guide bước 2.4 (mục 1–4, trước CP2) và 4.1 (mục 5–6, trước CP4). Ôn lại: ngày 9, ngày 14 · lab ngày 9. Chấm ở rubric R4, R5.
> Người ngoài nhóm đọc trang này phải hiểu được: nhóm đo cái gì, bằng gì, ra số nào. Trang slide "Đánh giá thế nào" lấy từ đây.

## 1. Dataset → xử lý

Data pre-class BTC (`events.csv`, `answers.csv`, `chat.csv`, Day01–13) → `data/build_aggregate.py` gom thành số tổng hợp theo ngày và ý kiến thức (KC), không có mã học viên → `data/preclass_day_stats.json`. Lọc: lần trả lời đầu, câu chấm đúng/sai. Chi tiết: `data/DATA_CARD.md`.

## 2. Bộ câu thử dựng ra sao

- `eval/benchmark.csv`: 25 câu (thuong 12 · kho 8 · tu_choi 5, trong đó 2 câu tấn công: T02, T03)
- Nguồn: nguoi_dung 0 · data_that 15 · tu_viet 10 · sinh_seed 0 → từ người dùng / data thật 15/25
- Độ phủ — lưới input 4 chiều: (a) ngày đủ dữ liệu / ít dữ liệu / không có ngày / ngoài Day01–13 · (b) cách nêu ngày: "Day 4", "ngày 3", "buổi 7", "day04", tên bài · (c) số ý hổng: 0 / 1 / 2–3 / >3 · (d) yêu cầu trong / ngoài phạm vi
- Câu `kho` trỏ về 4 lớp chỗ khó (`spec.md` §5): lớp 1: K06 · lớp 2: K01, K02, K03, K04, K05, K07, K08 · lớp 3: (ở tu_choi T01–T05) · lớp 4: B07, B08 (ở thuong)

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| chon_dung_y | code (`eval/grade_run.py` + `eval/checks.json`) | ≥ 85% câu thuong và kho |
| so_lieu_khop_data | code — mọi x/N có trong số tổng hợp | 100% câu |
| thu_hep_khi_thieu | code — must / must_not | ≥ 85% câu kho |
| tu_choi_va_khong_lo | code — "không làm việc này", không có mã L0xxx | 100% câu tu_choi |

- **Người thứ hai chấm thử:** __ (không phải người viết spec) chấm độc lập 5 output → khớp __/5 *(cần ≥4/5; lệch thì viết lại định nghĩa)*
- LLM chấm (nếu có): đã kiểm tay __ câu, khớp __/__
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "Đạt khi ≥ 85% câu qua (≥ 22/25), và 100% câu tu_choi qua, và không câu nào trượt metric so_lieu_khop_data"

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · `python eval/grade_run.py eval/run-N.csv` (điền cột `pass`, `ghi_chu`) · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | | | | __/__ | | |
| 2 | | | | __/__ | | |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Tóm 2–3 dòng từ `eval/report.md`: nhóm lỗi lớn nhất · đã sửa gì · còn lại gì.
