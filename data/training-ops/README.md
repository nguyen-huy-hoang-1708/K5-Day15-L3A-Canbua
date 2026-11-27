# Data pack — vận hành đào tạo: lịch, phòng, phân công *(giả lập)*

> `README.md` → `01-challenge-brief.md` → `tracks/` → **`data/training-ops/`** → `02-guide.md`
> Liên quan nhất tới **Track A**: hướng [A5 · Vận hành đào tạo](../../tracks/track-a-edtech.md#van-hanh-dao-tao) và [A2 · Trợ lý Discord](../../tracks/track-a-edtech.md#a2--trợ-lý-discord) (trả lời lịch, logistics có căn cứ).

Bộ này dựng lại cách một khoá AI20K **vận hành lịch học**:
- Ban đào tạo mở form cho giảng viên đăng ký buổi, rồi phân công giảng viên theo phòng.
- Đội lab coach xếp ca lab và đổi ca qua form riêng.
- Học viên nhận lịch qua email, tra lớp và nhóm của mình trong một danh sách chung của khoá.

Bối cảnh vận hành (khoá thiếu cơ sở vật chất, phòng học không cố định, nhiều phòng chỉ chốt sát ngày): [track A → Vận hành đào tạo](../../tracks/track-a-edtech.md#van-hanh-dao-tao).

**Cấu trúc file, tên sheet, tên cột và cách ghi** được dựng theo các bảng tính thật của khoá. **Người, email, mã và ngày đều là giả.** Khoá trong data là "Khoá 9", học từ 15/04 đến 08/05/2027.

**Mỗi file là bản tại một thời điểm**, như khi mở một bảng tính đang được sửa. Bảng phân công là bản xuất lúc **21:00 ngày 27/04/2027** (ghi ở ô D1 sheet `Khoá 9 (GĐ1)`); bảng lab coach và bản chép lịch trong đó được cập nhật lần cuối vào những lúc khác.

- **Dùng để:** hình dung workflow hiện tại trông thế nào, và dựng, chạy thử sản phẩm (ví dụ làm nguồn cho trợ lý trả lời lịch).
- **Không phải bằng chứng pain** ([đề bài → Data](../../01-challenge-brief.md#data)). Bằng chứng phải đến từ người dùng thật. Muốn hiểu sâu cách đang làm, hãy phỏng vấn lab coach, key coach, ban đào tạo, giảng viên (xem file track).

**Data không kèm gợi ý hay đáp án.** File này chỉ mô tả dữ liệu.

---

## Ngoài đời, file nào là gì

| File | Ngoài đời là | Ai ghi | Ai đọc |
|---|---|---|---|
| `teaching-schedule.xlsx` | Bảng phân công giảng dạy theo phòng | Ban đào tạo · giảng viên điền form đăng ký | Giảng viên · lab coach |
| `lab-coach-schedule.xlsx` | Bảng vận hành đội lab coach | Key coach · ban đào tạo · lab coach điền form đổi buổi | Lab coach |

## Quy mô

| | Số |
|---|---|
| Buổi học của Khoá 9 (mỗi lớp một buổi tính là một) | 111, trong 21 ngày học |
| Lớp | L3A, L3B (level 3–4) · L2A, L2B (level 2–3) |
| Lượt đăng ký lịch giảng dạy | 204 dòng, 32 người |
| Lịch sử chỉnh sửa bảng lịch (đến lúc xuất) | 44 dòng |
| Giảng viên · hỗ trợ · lab coach | 22 · 8 · 62 |

## Đã giả lập thế nào

- **Không có tên người.** Mọi người đều được ghi bằng nhãn:
  - Giảng viên: `Lecturer A`, `Lecturer B`…
  - Người hỗ trợ: `Support A`…
  - Lab coach: `Lab Coach A`… (quá 26 người thì `Lab Coach AA`, `AB`…)
- **Email** tạo từ nhãn, đều dưới tên miền `.example`, không gửi được.
- **Link** cũng dưới tên miền `.example`, không mở được.
- **Không có số điện thoại.**
- **Khoá, ngày** đều giả.
- **Mã phòng** (H209, C401…) và **chủ đề buổi học** giữ theo khoá thật để data giống thật.

---

## Các file

### `teaching-schedule.xlsx` — bảng phân công giảng dạy

| Sheet | Một dòng là | Cột |
|---|---|---|
| `Dang_ky_chi_tiet` | Một người đăng ký một buổi, qua form "Đăng ký lịch giảng dạy" | `Timestamp` (giờ gửi form) · `Họ tên đăng ký` (như người điền gõ) · `Email` · `Tên khớp chuẩn` · `Vai trò nguồn` (người điền tự chọn) · `Vai trò xếp vào file tổng hợp` · `Ngày` · `Ngày học` · `Buổi` · `Chuyên đề` · `Mục lịch gốc` (nguyên văn lựa chọn trong form) · `Đăng ký lặp?` |
| `Nhan_su` | Một người đã đăng ký | `Họ tên đăng ký` · `Tên khớp chuẩn` · `Vai trò nguồn` · `Vai trò xếp vào file tổng hợp` · `Số buổi đăng ký` |
| `Tong_hop` | Một buổi của lớp L3 | `Ngày` · `Ngày học` · `Buổi` · `Chuyên đề` · `Giảng viên phụ trách` · `Lab Coach phụ trách` · `Người đăng ký khác / chưa xác định vai trò` (ở sheet này "phụ trách" là những người **đã đăng ký** buổi đó) · `Tất cả người đăng ký` · `Số GV` · `Số Lab Coach` · `Số khác` · `Tổng phụ trách` · `Ghi chú` (các nhãn rà soát, nối bằng `\|`) |
| `Canh_bao` | Một nhãn rà soát của một buổi | `Mức độ` · `Loại` · `Ngày học` · `Buổi` · `Chuyên đề` · `Chi tiết` |
| `Khoá 9 (GĐ1)` | Một buổi (sáng hoặc chiều) của một ngày | Xem dưới |
| `Lịch sử chỉnh sửa` | Một lần sửa ô trong sheet `Khoá 9 (GĐ1)`, trích từ lịch sử phiên bản của bảng tính, tới lúc xuất file | `Thời điểm sửa` · `Người sửa` · `Sheet` · `Ô` (địa chỉ ô trong bản xuất) · `Buổi` (ngày, buổi, lớp — loại số buổi) · `Trước` · `Sau` |
| `Khoá 8 (GĐ2)` | Một buổi, giai đoạn 2 của khoá trước | `Thứ` · `Ngày` · `Buổi` · một cột cho mỗi track (tiêu đề cột ghi phòng). Ô ghi `Track — mã session — chủ đề`, dòng cuối ghi giảng viên |

**Sheet `Khoá 9 (GĐ1)`:**
- 3 dòng đầu là link (giả) tới form đăng ký và nội dung lớp. Dòng 4–5 là tiêu đề.
- Mỗi ngày có 2 dòng: `Sáng (09:00 - 13:00)` và `Chiều (14:00 - 18:00)`.
- Các cột:
  - Cột D, E: buổi LEC của L3, tiêu đề cột ghi H209 và H210. Một lớp L3 học LEC chia hai phòng song song. Hôm học phòng khác tiêu đề cột thì trong ô có dòng `Phòng: <mã phòng>`.
  - Cột F: buổi LAB của L3.
  - Cột G, H: lớp L2A, L2B.
- **Mỗi ô là chữ nhiều dòng**, theo thứ tự:
  - `lớp — LEC/LAB số buổi`
  - `Online` (nếu có)
  - giờ riêng (nếu khác khung của buổi)
  - chủ đề
  - `Phòng:` · `Phòng thêm:` · hoặc, khi phòng chưa được xác nhận lúc xuất file, `Phòng: chờ xác nhận` / `Phòng dự kiến: … (chờ xác nhận)`
  - `Giảng Viên:`
- Ô trống ghi `không có lớp`.
- **Ô gộp:** cột ngày (gộp dọc 2 dòng); buổi online gộp hai lớp (gộp ngang); khai giảng; nghỉ lễ.
- **Màu nền:** xanh dương là LEC, xanh lá là LAB, vàng là online, xám là nghỉ.

### `lab-coach-schedule.xlsx` — bảng vận hành đội lab coach

| Sheet | Là gì | Cột |
|---|---|---|
| `Master Plan` | Văn bản: mô hình 3 vai (Day Lead, lead theo phòng, lab coach), các mốc từ T-5 đến ngày dạy, quy tắc, cách đánh giá coach | — |
| `Lịch lớp K9 (bản chép)` | Lịch lớp chép sang file này. Ngày chép ghi ở ô D1 | Như sheet `Khoá 9 (GĐ1)` ở trên |
| `Lịch lab 1504-2404` | Ca lab đợt 1. Mỗi ngày một khối: dòng tiêu đề ngày, dòng tên cột, rồi mỗi dòng **một coach** | `STT` · `Lớp` · `Session` · `Lab Coach` · `Key Coach` · `Buổi` · `Sức chứa phòng` · `T-3 <ngày> / Ghi chú` · `Trạng thái` |
| `Lịch lab 2604-0805` | Ca lab đợt 2, cùng kiểu khối theo ngày | `STT` · `Lớp` · `Session` · `Lab Coach` · `Key Coach` · `Phòng` · `Buổi` · `Sức chứa phòng` · (cột trống) · `Trạng thái`. Cột `Phòng` ghi `chờ xác nhận` hoặc `dk: …` (dự kiến) khi phòng chưa chốt. Cột K–P (chữ xám) lặp lại `Ngày`, `Lớp`, `Session`, `Phòng`, `Buổi`, `Key Coach` cho từng dòng. Cột R: link form đổi buổi, chú thích màu, link nhóm Zalo (giả) |
| `Đổi buổi (form)` | Một yêu cầu đổi ca của lab coach, qua form | `Dấu thời gian` · `Họ tên` · `Email` · `Buổi đang nhận` · `Muốn đổi sang` (chữ tự do) · `Lý do` · `Đã xử lý?` · `Ghi chú BTC` |
| `Workload - Lab coach` | Ma trận ca: mỗi dòng một coach, mỗi ngày 3 cột `S` / `C` / `T` (sáng, chiều, tối) | `STT` · `Khoá` (khoá coach từng học) · `Thành viên` · các ô ca · cuối dòng: `Số ca Key`, `Số ca Lab`, `Tổng ca`, `% buổi có mặt`, `Giờ quy đổi`. Giá trị ô: `K` = ca key coach, `L` = ca lab coach, `L!` = ca được đánh dấu trùng. Dòng 2: các số tổng hợp (giờ / ca, hệ số quy đổi, số buổi có phân công…) |

Trong hai sheet lịch lab, **ô gộp** theo nhóm (lớp, session, key coach, buổi… chỉ ghi ở dòng đầu nhóm). **Màu nền ô Lab Coach** cho biết coach thuộc khoá nào; chú thích màu ở dòng tiêu đề hoặc cột R.

---

## Nối các file

- **Buổi học** được gọi bằng lớp + loại buổi + số buổi + ngày, ví dụ `L3A — LAB 4` trong ô lịch, và `Lớp` = `L3A`, `Session` = `LAB 4` trong sheet lịch lab. Không có mã buổi chung giữa các file.
- **Người** (giảng viên, lab coach): `Tên khớp chuẩn` trong `Nhan_su` là nhãn dùng ở các sheet lịch và workload. Email trong form đổi buổi khớp email đăng ký.
- **Lớp:** `L3A`, `L3B`, `L2A`, `L2B`; buổi gộp hai lớp ghi `L3AB`, `L2AB`, `L2A+B`.

## Đọc file

```python
import pandas as pd                      # cần thêm: python -m pip install pandas openpyxl
sheets = pd.read_excel("teaching-schedule.xlsx", sheet_name=None)   # dict: tên sheet → bảng
```

- Ô gộp đọc bằng pandas sẽ ra **trống ở các dòng sau** của nhóm.
- Màu nền và link trong ô chỉ đọc được bằng `openpyxl` (`cell.fill.start_color`, `cell.hyperlink`), hoặc mở file bằng Excel / Google Sheets.
- `starter-repo` mặc định không cần thư viện ngoài. Dùng bộ này thì ghi `pandas` và `openpyxl` vào `requirements.txt` của nhóm.
- Dựng bản chạy thử trên bộ này thì ghi vào `data/DATA_CARD.md`: dùng file nào, xử lý gì ([guide 2.4](../../02-guide.md#b2-4)).
