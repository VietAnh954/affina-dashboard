# 🔧 TROUBLESHOOTING — Cẩm nang xử lý lỗi

> Danh sách này gom mọi lỗi thường gặp khi build & deploy Affina Dashboard. **Đọc theo mã lỗi hoặc theo tình huống**.

---

## 📑 Mục lục

1. [Lỗi Python / môi trường local](#1-lỗi-python--môi-trường-local)
2. [Lỗi Google Drive / OAuth](#2-lỗi-google-drive--oauth)
3. [Lỗi Supabase / PostgreSQL](#3-lỗi-supabase--postgresql)
4. [Lỗi DuckDB / pandas](#4-lỗi-duckdb--pandas)
5. [Lỗi GitHub Actions](#5-lỗi-github-actions)
6. [Lỗi Streamlit / dashboard hiển thị](#6-lỗi-streamlit--dashboard-hiển-thị)
7. [Lỗi khi share link](#7-lỗi-khi-share-link)

---

## 1. Lỗi Python / môi trường local

### 1.1 `pip install psycopg2-binary` fail trên Windows

**Lỗi:**
```
ERROR: Failed building wheel for psycopg2-binary
```

**Nguyên nhân:** Version Python 3.13 chưa có prebuilt wheel cho psycopg2-binary.

**Fix:**
```powershell
# Cài Python 3.12 thay vì 3.13
# Hoặc dùng flag --only-binary
pip install psycopg2-binary --only-binary :all:
```

### 1.2 `ModuleNotFoundError: No module named 'lib'`

**Lỗi khi chạy `streamlit run dashboard.py`:**
```
ModuleNotFoundError: No module named 'lib'
```

**Nguyên nhân:** Đang chạy Streamlit từ folder không có `lib/`.

**Fix:** Vào đúng folder root chứa `dashboard.py`:
```powershell
cd C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test
streamlit run dashboard.py
```

Kiểm tra `lib/__init__.py` tồn tại:
```powershell
dir lib
```

Nếu vẫn lỗi trên Streamlit Cloud → kiểm tra `.gitignore` không có dòng `lib/`. Nếu có, comment out dòng đó.

### 1.3 `UnicodeEncodeError` khi log tiếng Việt trên Windows

**Fix:** Set encoding UTF-8 ở terminal:
```powershell
chcp 65001
$env:PYTHONIOENCODING = "utf-8"
```

Hoặc thêm vào đầu script:
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

Script `build_dashboard_data.py` đã có `log()` function không dùng emoji, tránh vấn đề này.

### 1.4 `.env` không được load

**Fix:** Verify `python-dotenv` đã cài:
```powershell
pip show python-dotenv
```

Đảm bảo `.env` ở cùng thư mục với script. Nếu chạy từ folder khác, dùng path tuyệt đối:
```python
from dotenv import load_dotenv
load_dotenv(r"C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test\.env")
```

---

## 2. Lỗi Google Drive / OAuth

### 2.1 `HttpError 403: access_denied`

**Lỗi khi chạy `get_refresh_token.py`:**
```
Lỗi 403: access_denied
"dailyanloan chưa hoàn tất quy trình xác minh của Google"
```

**Fix:**
1. Vào Google Cloud Console → **APIs & Services** → **OAuth consent screen**
2. Scroll xuống **Test users** → **+ Add Users**
3. Nhập email Gmail đang dùng (`vietanh954@gmail.com` hoặc email liên quan)
4. **Save**
5. Chạy lại script

### 2.2 `HttpError 403: Service Accounts do not have storage quota`

**Bối cảnh:** Đã cố dùng Service Account thay OAuth.

**Fix:** **KHÔNG dùng Service Account cho Drive cá nhân** (Gmail). Google đã cấm SA tạo file mới trên Drive Gmail. Chỉ Google Workspace + Shared Drive mới dùng được SA.

→ Dùng OAuth Refresh Token (đã có script trong repo `daily-report-affina`).

### 2.3 `refresh_token has been expired or revoked`

**Fix:** Chạy lại `get_refresh_token.py`:
```powershell
python get_refresh_token.py
```
Lấy `GOOGLE_REFRESH_TOKEN` mới, update GitHub Secret.

**Cách kiểm tra token có valid không:**
```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

creds = Credentials(
    token=None,
    refresh_token="YOUR_REFRESH_TOKEN",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    token_uri="https://oauth2.googleapis.com/token",
)
try:
    creds.refresh(Request())
    print("✅ Token OK, expires:", creds.expiry)
except Exception as e:
    print("❌ Token invalid:", e)
```

### 2.4 `FileNotFoundError: Không tìm thấy file DSNS...`

**Nguyên nhân:** File `DSNS CTV sale Affina NEW - HR NHẬP.xlsx` không ở folder `Data`.

**Fix:** Script `build_dashboard_data.py` đã tự fallback tìm ở folder `Nhân sự sales` rồi tìm toàn Drive. Nếu vẫn không thấy:

1. Vào Google Drive, tìm file → confirm nó tồn tại và tài khoản OAuth có quyền truy cập.
2. Đảm bảo tên file **KHỚP CHÍNH XÁC** (kể cả space, dấu tiếng Việt).
3. Nếu tên file thay đổi, sửa constant `DSNS_FILE_NAME` trong `scripts/build_dashboard_data.py`.

### 2.5 `HttpError 429: too many requests`

**Nguyên nhân:** Google Drive API rate limit.

**Fix:** Retry với exponential backoff. Rất hiếm gặp với volume của Affina.

---

## 3. Lỗi Supabase / PostgreSQL

### 3.1 `psycopg2.OperationalError: connection timeout`

**Nguyên nhân:** Supabase free tier pause project sau nhiều ngày không dùng, hoặc network flaky.

**Fix:**
1. Vào Supabase Studio → nhấn nút "Restore" nếu project đang paused.
2. `create_engine(URI, pool_pre_ping=True)` đã bật (giúp health-check trước query).
3. Nếu vẫn lỗi, retry 2-3 lần với sleep:
   ```python
   import time
   for attempt in range(3):
       try:
           engine = create_engine(SUPABASE_DB_URI, pool_pre_ping=True)
           engine.connect().close()
           break
       except Exception as e:
           print(f"Attempt {attempt+1} failed: {e}")
           time.sleep(5)
   ```

### 3.2 `password authentication failed`

**Nguyên nhân:** Password trong URI không đúng, hoặc có ký tự đặc biệt chưa URL-encode.

**Fix:**
- Password có `@` → phải encode thành `%40`
- Password có `:` → thành `%3A`
- Password có `#` → thành `%23`

Ví dụ password `Affina@2025` → URI phải là:
```
postgresql://postgres.xxx:Affina%402025@aws-1-ap-south-1.pooler.supabase.com:6543/postgres
```

### 3.3 `too many connections for role`

**Nguyên nhân:** Supabase free có pool ~50 connection. Nhiều Streamlit visitor + Actions job → overload.

**Fix:**
- `@st.cache_resource` cho `create_engine()` → chỉ tạo 1 engine per app instance.
- `@st.cache_data(ttl=300)` cho query → 5 phút mới hit DB 1 lần.
- Đóng connection sau dùng: `with engine.connect() as conn: ...`

### 3.4 Bảng `dashboard_master_data` không tồn tại

**Lỗi khi mở dashboard lần đầu:**
```
relation "dashboard_master_data" does not exist
```

**Fix:** Chạy build script lần đầu:
```powershell
# Local:
python scripts/build_dashboard_data.py

# Hoặc trên GitHub: Actions → Build Dashboard Data → Run workflow
```

Dashboard sẽ tự hướng dẫn nếu bảng chưa có (đã handle trong `dashboard.py`).

### 3.5 Egress limit 5GB/tháng

**Fix:**
- Cache TTL 5 phút giúp giảm read.
- Nếu > 100 concurrent users, cân nhắc paid tier ($25/tháng).
- Hoặc dump `dashboard_master_data` xuống Parquet mỗi ngày → host trên GitHub → Streamlit đọc từ GitHub raw (miễn phí, nhanh hơn).

---

## 4. Lỗi DuckDB / pandas

### 4.1 `duckdb.CatalogException: Table "df_ns" does not exist`

**Nguyên nhân:** Chưa register df vào duckdb.

**Fix:** Script đã register:
```python
con.register("df_ns", df_ns)
con.register("qd1", qd1)
con.register("df_union", df_union)
```

Nếu tự sửa script, phải register lại.

### 4.2 `TypeError: Object of type Timestamp is not JSON serializable`

**Xuất hiện khi push lên Supabase/Google Sheet.**

**Fix:** Convert datetime → string trước khi push:
```python
df["Ngày thanh toán"] = df["Ngày thanh toán"].dt.strftime("%Y-%m-%d")
```

Hoặc dùng `pandas.to_sql()` (handle sẵn).

### 4.3 `SettingWithCopyWarning`

**Nguyên nhân:** Modify slice của DataFrame.

**Fix:** Dùng `.copy()`:
```python
df_bhsk = df[df["Loại bảo hiểm"] == "BHSK"].copy()
```

Chỉ là warning, không blocking. Đã handle trong code.

### 4.4 Số tiền không đúng — VD hiện 1000 thay vì 1000000

**Nguyên nhân:** Cột `Số tiền thanh toán` bị parse sai format.

**Fix:** Xem hàm `clean_currency_column()` trong `build_dashboard_data.py`. Có logic: nếu số < 1000 → nhân 1000 (giả định đơn vị nghìn VNĐ). Nếu Affina thay đổi format, sửa hàm này.

---

## 5. Lỗi GitHub Actions

### 5.1 Workflow không tự chạy đúng giờ

**Symptom:** Set cron 10:00 VN nhưng workflow chạy lúc 10:15 hoặc 10:30.

**Nguyên nhân:** GitHub Actions cron **CHẬM 5-30 phút** vào free tier do hàng đợi. Đây là **hành vi bình thường**, không phải bug.

**Workaround:** Nếu cần chính xác giờ, deploy trên VPS riêng với `cron` thật.

### 5.2 Workflow không xuất hiện trong tab Actions

**Nguyên nhân:** File `.github/workflows/build_dashboard.yml` chưa được commit / có lỗi YAML.

**Fix:**
1. Check syntax:
   ```powershell
   # Cài yamllint
   pip install yamllint
   yamllint .github/workflows/build_dashboard.yml
   ```
2. Verify path đúng: `.github/workflows/*.yml` (không phải `.github/workflow/`)
3. Nếu vẫn không xuất hiện → push lại:
   ```powershell
   git add .github/
   git commit -m "fix: add workflow"
   git push
   ```

### 5.3 `secrets.SUPABASE_DB_URI` là empty

**Symptom:** Log ra `[ERROR] Thiếu env: ['SUPABASE_DB_URI']`

**Fix:**
1. Vào repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `SUPABASE_DB_URI` (chú ý CASE-SENSITIVE, phải đúng chữ hoa)
4. Secret: paste connection string
5. Add secret

Lặp lại với 3 secrets còn lại.

### 5.4 Workflow chạy nhưng exit code 1

**Fix:** Vào Actions → Click vào run failed → **Xem log** → tìm dòng có `[FATAL]` hoặc `Traceback`.

Copy log vào ChatGPT/agent để phân tích.

### 5.5 Timeout (workflow > 20 phút)

**Nguyên nhân:** Data quá lớn hoặc network chậm.

**Fix:**
1. Nếu `df_master` > 500k rows → filter data cũ (VD chỉ giữ 2024-2026):
   ```python
   START_YEAR = 2024
   END_YEAR   = 2026
   ```
2. Tăng timeout trong workflow:
   ```yaml
   timeout-minutes: 40
   ```
3. Optimize push (batch nhỏ hơn, hoặc dùng `COPY` thay `INSERT`).

---

## 6. Lỗi Streamlit / dashboard hiển thị

### 6.1 App bị "This app has gone to sleep"

**Nguyên nhân:** Free Streamlit Cloud sleep sau **7 ngày không có visitor**.

**Fix:** Click nút **"Yes, get this app back up!"** — chờ ~30s.

**Prevention:** Nếu team dùng hàng ngày → không bao giờ sleep.

### 6.2 `KeyError: 'SUPABASE_DB_URI'` trên Streamlit Cloud

**Fix:**
1. Streamlit Cloud dashboard → app → **⋮** → **Settings** → **Secrets**
2. Paste:
   ```toml
   SUPABASE_DB_URI = "postgresql://postgres.xxx:PASSWORD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
   ```
3. Save → app tự reboot

### 6.3 Chart không hiển thị / trống trơn

**Nguyên nhân thường gặp:**
- Filter loại trừ hết data
- Column name có typo
- Data column là `object` thay vì `numeric`

**Debug:**
```python
# Thêm tạm vào page
st.write(df.head())
st.write(df.dtypes)
st.write("Rows sau filter:", len(df))
```

### 6.4 Dashboard rất chậm (>10s load)

**Fix:**
1. Verify cache TTL:
   ```python
   @st.cache_data(ttl=300)  # 5 phút
   def load_master_data(): ...
   ```
2. Không load full `SELECT *` nếu không cần — filter tại DB:
   ```python
   pd.read_sql("SELECT ... WHERE ... ", engine)
   ```
3. Convert cột string dài → category:
   ```python
   df["Channel"] = df["Channel"].astype("category")
   ```

### 6.5 Font tiếng Việt hiển thị lỗi

**Fix:** Add font Google Noto Sans vào `.streamlit/config.toml`:
```toml
[theme]
font = "sans serif"
```
Hoặc dùng font emoji `serif`. Streamlit sẵn support Unicode.

### 6.6 Sidebar filter reset sau mỗi lần click chart

**Nguyên nhân:** Không lưu state.

**Fix:** Add `key=` cho mọi widget:
```python
st.multiselect("Source", options=..., default=..., key="source_filter")
```

(Đã handle trong `lib/data.py`).

### 6.7 Deploy lần đầu bị lỗi "requirements.txt not found"

**Fix:** Verify `requirements.txt` ở root repo (không phải trong subfolder).

---

## 7. Lỗi khi share link

### 7.1 "Sorry, this app doesn't exist"

**Fix:** Verify URL đúng. Format: `https://<app-name>.streamlit.app` (không phải `.io`, `.com`).

### 7.2 Người khác click link phải login

**Nguyên nhân:** App đang ở private mode.

**Fix:** Streamlit Cloud dashboard → app → **Settings** → **Sharing** → chọn **Public**.

### 7.3 App live nhưng chart không có data

**Nguyên nhân:**
- Job GH Actions chưa chạy → `dashboard_master_data` trống
- Sai secret `SUPABASE_DB_URI`

**Fix:**
1. Vào GH Actions → verify run "Build Dashboard Data" **green ✅**
2. Vào Supabase → SQL Editor → `SELECT COUNT(*) FROM dashboard_master_data;`
3. Nếu > 0 → check Streamlit secret

---

## 🆘 Vẫn không giải quyết được?

1. Copy full stack trace từ log
2. Note lại: bước nào, môi trường nào (local/Actions/Streamlit)
3. Ping cho VietAnh trên Slack/Zalo với:
   - Screenshot lỗi
   - Log file (`.log` từ Actions hoặc terminal)
   - Câu hỏi cụ thể

4. Fallback: rollback về Excel manual output cho tuần này, debug thứ 7 chủ nhật.

---

## 🔍 Debug commands hay dùng

```powershell
# Test kết nối Supabase
python -c "from sqlalchemy import create_engine; e=create_engine('postgresql://...'); print(e.connect().execute('SELECT 1').scalar())"

# Xem log 100 dòng cuối của GH Actions
gh run view --log | tail -100  # cần cài GitHub CLI

# Streamlit debug mode
streamlit run dashboard.py --logger.level debug

# Verify Python version
python -VV

# List tất cả env vars đang set (đừng share output vì có secret)
python -c "import os; [print(f'{k}={v[:5]}...') for k,v in os.environ.items() if 'SUPA' in k or 'GOOGLE' in k]"
```
