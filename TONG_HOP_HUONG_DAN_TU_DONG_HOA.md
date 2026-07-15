# Hướng dẫn hoàn chỉnh: Tự động hóa Google Colab Notebook chạy trên GitHub Actions

## Tổng quan dự án

**Mục tiêu:** Chuyển file Google Colab notebook (`Daily_ AN/LOAN.ipynb`) từ chạy thủ công → chạy tự động hàng ngày lúc 17:00 VN, hoàn toàn online, không cần người thao tác.

**Kết quả đạt được:**
- Notebook Colab được chuyển thành Python script chạy trên GitHub Actions (miễn phí)
- Tự động: tải data từ Google Drive → xử lý → đẩy Supabase → chạy DuckDB queries → xuất Excel → upload lại Drive
- Lịch chạy: 17:00 VN mỗi ngày (cron `0 10 * * *` UTC)
- Notebook gốc trên Colab vẫn giữ nguyên để debug khi cần

**Tech stack:** Python 3.12, GitHub Actions, Google Drive API (OAuth), Supabase (PostgreSQL), DuckDB, pandas, openpyxl

---

## Kiến trúc hệ thống

```
GitHub Actions (cron 17:00 VN)
    │
    ├── Checkout code từ repo
    ├── Setup Python 3.12 + install dependencies
    ├── Chạy daily_report.py
    │     ├── Kết nối Google Drive bằng OAuth Refresh Token
    │     ├── Tải 3 file input (DSNS, QuyDoi, CapDon Google Sheet)
    │     ├── Làm sạch data (pandas)
    │     ├── Đẩy data lên Supabase (3 bảng)
    │     ├── Chạy DuckDB queries (Detail, DSA, BDM, BDD, Tái tục)
    │     ├── Xuất 2 file Excel (An + Loan) với format
    │     └── Upload 4 file Excel lên Google Drive (2 folder mỗi file)
    └── Done
```

---

## Cấu trúc repository GitHub

```
daily-report-affina/          (Private repo)
├── .github/
│   └── workflows/
│       └── daily_report.yml   # Lịch chạy + env secrets
├── daily_report.py            # Script chính (697 dòng, giữ nguyên logic notebook)
├── requirements.txt           # 9 thư viện Python
├── README.md
└── (các file phụ: fix_and_push.ps1, files/, new/)
```

---

## Chi tiết từng bước đã thực hiện

### BƯỚC 1: Phân tích notebook Colab gốc

**File gốc:** `Daily_ AN/LOAN.ipynb` trên Google Colab

**Cấu trúc notebook:**
1. **Cell 1 - Kết nối:** `drive.mount()` + `auth.authenticate_user()` (cần popup thủ công)
2. **Cell 1.5 - Đồng bộ DSNS:** Copy file từ `Othercomputers/My Laptop/Nhân sự sales/` sang `MyDrive/AFFINA/Data/`
3. **Cell 2 - Đọc data:** 3 nguồn (DSNS Excel, QuyDoi Excel, CapDon Google Sheet với 7 sheet)
4. **Cell 2.x - Làm sạch:** Chuẩn hóa ngày, tiền tệ, whitespace, hợp đồng, channel
5. **Cell 2.4 - Gộp data:** `pd.concat()` 7 loại bảo hiểm
6. **Cell 3 - Push Supabase:** 3 bảng (qd1, ds_nhan_su_affina, union_all_data_cap_don)
7. **Cell 3 - DuckDB queries:** 10 câu SQL phức tạp (QUERY_DETAIL, QUERY_DSA, QUERY_BDM, QUERY_BDD, BASE_RENEW + 5 query tái tục)
8. **Cell 3 - Xuất Excel:** 2 file (An + Loan), mỗi file 5 sheet
9. **Cell 4 - Format Excel:** Header, border, number format, auto-filter, freeze pane
10. **Cell 5 - Upload Drive:** 4 file Excel → 4 folder khác nhau trên Drive

**Vấn đề cốt lõi:** `drive.mount()` và `auth.authenticate_user()` yêu cầu popup OAuth tương tác → không thể tự động hóa trên Colab.

### BƯỚC 2: Chuyển notebook thành Python script

**Nguyên tắc:** Giữ nguyên 100% logic nghiệp vụ, chỉ thay đổi cách kết nối Google Drive.

**Thay đổi duy nhất:**
- `drive.mount('/content/drive')` → Google Drive API với OAuth Refresh Token
- `auth.authenticate_user()` → Không cần (OAuth token thay thế)
- Đường dẫn file `/content/drive/MyDrive/...` → Google Drive API `find_file()` + `download_file()`

**Các hàm helper đã tạo:**
```python
find_file_in_drive(file_name, parent_folder_name)  # Tìm file theo tên
download_file_from_drive(file_id, local_path)       # Tải file về
export_google_sheet(file_id, local_path)             # Export Sheet → xlsx
find_or_create_folder(folder_name, parent_id)        # Tìm/tạo folder
upload_file_to_drive(local_path, folder_id)          # Upload file (ghi đè nếu tồn tại)
```

**Toàn bộ SQL queries (10 câu) được copy nguyên từ notebook:**
- `QUERY_DETAIL` — Chi tiết giao dịch theo BDD
- `QUERY_DSA` — Tracking DSA (agent bán hàng)
- `QUERY_BDM` — Tracking BDM (quản lý cấp 1) với KPI
- `QUERY_BDD` — Tracking BDD (quản lý cấp 2) với KPI
- `BASE_RENEW` — CTE cơ sở cho tái tục BHSK
- `QUERY_THEODOI` — Chi tiết theo dõi tái tục
- `QUERY_THONGKE` — Thống kê tái tục theo trạng thái
- `QUERY_TILE` — Tỉ lệ tái tục theo tháng
- `QUERY_TT_BDM` — Tái tục theo BDM
- `QUERY_TT_BDD` — Tái tục theo BDD

### BƯỚC 3: Xác thực Google Drive — Hành trình giải quyết lỗi

#### Lần 1: Service Account (THẤT BẠI)

**Cách làm ban đầu:**
1. Tạo Google Cloud Project
2. Bật Google Drive API + Google Sheets API
3. Tạo Service Account → download JSON key
4. Chia sẻ Drive folders + Google Sheet cho SA email
5. Dùng `service_account.Credentials.from_service_account_file()`

**Lỗi gặp phải:**
```
HttpError 403: "Service Accounts do not have storage quota.
Leverage shared drives or use OAuth delegation instead."
```

**Nguyên nhân:** Google đã thay đổi chính sách — Service Account không còn được tạo file mới trên Google Drive cá nhân (0 storage quota). SA chỉ có thể đọc và cập nhật file đã tồn tại.

**Kết luận:** Service Account KHÔNG phù hợp cho Drive cá nhân (Gmail). Chỉ dùng được với Google Workspace + Shared Drives.

#### Lần 2: OAuth Refresh Token (THÀNH CÔNG)

**Cách làm thay thế:**
1. Tạo OAuth Client ID (Desktop app) trên Google Cloud Console
2. Cấu hình OAuth Consent Screen (External, Testing mode)
3. Thêm email người dùng vào Test Users
4. Chạy script `get_refresh_token.py` trên máy local 1 lần
5. Lưu 3 giá trị vào GitHub Secrets

**Code xác thực (thay thế SA):**
```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('GOOGLE_REFRESH_TOKEN')

credentials = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri='https://oauth2.googleapis.com/token',
)
credentials.refresh(Request())
drive_service = build('drive', 'v3', credentials=credentials)
```

**Script lấy Refresh Token (`get_refresh_token.py`):**
```python
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file("oauth_credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

with open("oauth_credentials.json") as f:
    oauth_info = json.load(f)
    installed = oauth_info.get("installed", oauth_info.get("web", {}))

print(f"GOOGLE_CLIENT_ID: {installed['client_id']}")
print(f"GOOGLE_CLIENT_SECRET: {installed['client_secret']}")
print(f"GOOGLE_REFRESH_TOKEN: {creds.refresh_token}")
```

### BƯỚC 4: Cấu hình OAuth Consent Screen

**Lỗi gặp phải khi chạy `get_refresh_token.py`:**
```
Lỗi 403: access_denied
"dailyanloan chưa hoàn tất quy trình xác minh của Google"
```

**Nguyên nhân:** App OAuth đang ở chế độ "Testing" → chỉ Test Users mới được truy cập.

**Cách sửa:**
1. Google Cloud Console → Google Auth Platform → Audience
2. Test users → Add users → nhập email Gmail của user
3. Save → chạy lại `get_refresh_token.py`

### BƯỚC 5: Xử lý lỗi tìm file trên Drive

**Lỗi:**
```
FileNotFoundError: Không tìm thấy file DSNS CTV sale Affina NEW - HR NHẬP.xlsx trên Google Drive!
```

**Nguyên nhân:** Trong notebook Colab, file DSNS nằm ở `Othercomputers/My Laptop/Nhân sự sales/` và được copy sang `MyDrive/AFFINA/Data/`. Trên GitHub Actions, không có bước copy này, và hàm `find_file_in_drive()` chỉ tìm trong folder "Data".

**Cách sửa:** Thêm fallback tìm toàn bộ Drive nếu không thấy trong folder "Data":
```python
dsns_file_id = find_file_in_drive(DSNS_FILE_NAME, "Data")
if not dsns_file_id:
    print("  Khong thay trong Data, tim toan bo Drive...")
    dsns_file_id = find_file_in_drive(DSNS_FILE_NAME)
```

### BƯỚC 6: GitHub Actions Workflow

**File `.github/workflows/daily_report.yml`:**
```yaml
name: Daily Report AN/LOAN

on:
  schedule:
    - cron: '0 10 * * *'    # 10:00 UTC = 17:00 VN
  workflow_dispatch:          # Cho phép chạy tay

jobs:
  run-report:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - name: Run Daily Report
        env:
          SUPABASE_DB_URI: ${{ secrets.SUPABASE_DB_URI }}
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          GOOGLE_REFRESH_TOKEN: ${{ secrets.GOOGLE_REFRESH_TOKEN }}
          TZ: Asia/Ho_Chi_Minh
        run: python daily_report.py
```

**GitHub Secrets cần thiết (4 secrets):**

| Secret | Nguồn |
|---|---|
| `SUPABASE_DB_URI` | Connection string PostgreSQL của Supabase |
| `GOOGLE_CLIENT_ID` | Từ OAuth Client ID (Google Cloud Console) |
| `GOOGLE_CLIENT_SECRET` | Từ OAuth Client ID (Google Cloud Console) |
| `GOOGLE_REFRESH_TOKEN` | Từ script `get_refresh_token.py` |

### BƯỚC 7: Đẩy code lên GitHub và test

**Cấu trúc local folder:**
```
C:\Users\ADMIN\Desktop\AFFINA\CODE\Test_auto_git\daily-report-affina\
├── .github\workflows\daily_report.yml
├── daily_report.py
├── requirements.txt
└── README.md
```

**Lệnh push:**
```powershell
cd "C:\Users\ADMIN\Desktop\AFFINA\CODE\Test_auto_git\daily-report-affina"
git add -A
git commit -m "message"
git push origin main
```

**Test thủ công:** GitHub repo → Actions → Daily Report AN/LOAN → Run workflow → Run workflow

**Kết quả:** Workflow chạy thành công trong ~3 phút, 4 file Excel được upload lên Google Drive.

---

## Các lỗi đã gặp và cách xử lý

| # | Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|---|
| 1 | `HttpError 403: Service Accounts do not have storage quota` | SA không có quota trên Drive cá nhân | Chuyển sang OAuth Refresh Token |
| 2 | `403: access_denied - chưa hoàn tất quy trình xác minh` | OAuth app ở chế độ Testing, email chưa được thêm | Thêm email vào Test Users trong Consent Screen |
| 3 | `FileNotFoundError: Không tìm thấy file DSNS` | File nằm ở Othercomputers, không nằm trong folder "Data" | Thêm fallback tìm toàn bộ Drive |
| 4 | PowerShell script lỗi encoding (`â†'`) | Ký tự Unicode trong file .ps1 bị hỏng | Viết lại script chỉ dùng ASCII |
| 5 | Scheduled workflow không chạy đúng giờ | GitHub Actions trễ 5-30 phút do hàng đợi | Hành vi bình thường, không phải lỗi |

---

## File requirements.txt

```
pandas
openpyxl
sqlalchemy
psycopg2-binary
duckdb
google-api-python-client
google-auth
google-auth-httplib2
google-auth-oauthlib
```

---

## Quy trình thay đổi lịch chạy

**Công thức:** Giờ VN - 7 = Giờ UTC

| Giờ VN | Cron (UTC) |
|---|---|
| 08:00 | `0 1 * * *` |
| 17:00 | `0 10 * * *` |
| 20:00 | `0 13 * * *` |
| 21:30 | `30 14 * * *` |
| 23:45 | `45 16 * * *` |

**Lệnh đổi lịch nhanh (PowerShell):**
```powershell
(Get-Content ".github\workflows\daily_report.yml" -Raw) -replace "cron: '0 10", "cron: '0 13" | Set-Content ".github\workflows\daily_report.yml" -Encoding UTF8 -NoNewline
git add -A && git commit -m "Schedule: 20:00 VN" && git push origin main
```

---

## Quy trình thêm file Colab mới vào hệ thống

1. Đọc file `.ipynb` mới, xác định: input files, output files, logic xử lý
2. Tạo file `ten_job_moi.py` — copy logic, thay `drive.mount()` bằng OAuth Drive API
3. Tạo file `.github/workflows/ten_job_moi.yml` — set cron riêng
4. Push lên GitHub → test bằng Run workflow
5. Dùng chung 4 GitHub Secrets đã có (không cần tạo thêm)

---

## Lưu ý quan trọng cho AI Agent

1. **KHÔNG dùng Service Account cho Drive cá nhân (Gmail)** — Google đã cấm tạo file mới. Phải dùng OAuth Refresh Token.

2. **OAuth Consent Screen phải ở chế độ Testing** và email user phải được thêm vào Test Users. Nếu không sẽ bị lỗi `access_denied`.

3. **Refresh Token không hết hạn** nếu app ở chế độ Testing và user không revoke. Tuy nhiên nếu user thay đổi mật khẩu Gmail hoặc revoke access, cần chạy lại `get_refresh_token.py`.

4. **File trên Drive có thể nằm ở nhiều nơi:** MyDrive, Othercomputers, Shared with me. Hàm `find_file_in_drive()` cần có fallback tìm toàn bộ Drive.

5. **GitHub Actions cron trễ 5-30 phút** là bình thường. Không đảm bảo chạy đúng phút.

6. **Giữ nguyên logic nghiệp vụ 100%** — chỉ thay đổi cách kết nối (Drive API thay drive.mount). Mọi SQL query, pandas transform, Excel formatting phải giữ nguyên.

7. **PowerShell trên Windows:** Tránh dùng ký tự Unicode trong file .ps1. Chỉ dùng ASCII để tránh lỗi encoding.

8. **Thứ tự ưu tiên khi tìm file trên Drive:** folder cụ thể trước → toàn bộ Drive sau. Tên file phải khớp chính xác.

9. **Google Sheet export:** Dùng `files().export_media()` với mimeType `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` để export thành .xlsx.

10. **Upload file lên Drive:** Kiểm tra file đã tồn tại → `update()`. Chưa tồn tại → `create()` với parent folder ID.

---

## Thông tin kết nối

- **GitHub repo:** `VietAnh954/daily-report-affina` (Private)
- **Google Cloud Project:** `Daily An Loan test1`
- **Supabase tables:** `qd1`, `ds_nhan_su_affina`, `union_all_data_cap_don`
- **Google Sheet ID (Cấp đơn):** `1qc_QhrvpoLLp6w9RkGBEkm8qBO49GJE8oMlwkCdJOsk`
- **Output folders trên Drive:** `AFFINA/Report/Report_Daily/An/`, `AFFINA/Report/Report_Daily/Loan/`, `Report_daily_An/`, `Report_daily_Loan/`
- **Input files:** `DSNS CTV sale Affina NEW - HR NHẬP.xlsx` (folder Data hoặc Nhân sự sales), `26_02_04_sửa ngày_quy_doi_all.xlsx` (folder Data)
