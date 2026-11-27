# Tóm tắt mô phỏng simulate-1@20261127-163014

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| giang_vien_lec | 22 | 2 | 2623 | 275 | 1.3 | 2.3 |
| lab_coach | 26 | 1 | 1323 | 123 | 0.7 | 1.2 |
| ban_dao_tao | 2 | 3 | 1488 | 162 | 1.0 | 2.5 |

Tỉ lệ đạt dùng để tính: 23/25 (92%) — lượt run-2@20261127-162833

- Tự chọn: lượt run-N mới nhất đã chấm xong, chạy bằng đúng model đang đo (run-2.csv). Muốn dùng lượt khác (vd lượt 2): thêm `--rate-from eval/run-2.csv`.

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (22 người) | Chi phí / tháng — cơ sở (50 người) | Chi phí / tháng — cao (92 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| claude-haiku-5-5 (vào 0.1 · ra 0.5 $/1M) | $0.00029 | $0.00031 | $0.00020 | $0.0397 | $0.0903 | $0.1662 | $0.0018 |
| claude-sonnet-5-5 (vào 2.0 · ra 10.0 $/1M) | $0.0057 | $0.0062 | $0.0041 | $0.7948 | $1.81 | $3.32 | $0.0361 |
| claude-opus-5-5 (vào 4.0 · ra 20.0 $/1M) | $0.0114 | $0.0124 | $0.0082 | $1.59 | $3.61 | $6.65 | $0.0723 |
| @cf/mistralai/mistral-small-3.1-24b-instruct (vào 0.351 · ra 0.555 $/1M) | $0.00077 | $0.00084 | $0.00055 | $0.1070 | $0.2432 | $0.4476 | $0.0049 |
| @cf/meta/llama-3.3-70b-instruct-fp8-fast (vào 0.293 · ra 2.253 $/1M) | $0.00099 | $0.0011 | $0.00071 | $0.1377 | $0.3131 | $0.5760 | $0.0063 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.5) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: @cf/mistralai/mistral-small-3.1-24b-instruct. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
