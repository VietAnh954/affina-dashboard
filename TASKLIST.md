# ✅ TASKLIST — Full checklist triển khai Affina Dashboard

> Đánh dấu ✅ cho mỗi task hoàn thành. Nếu gặp lỗi → xem `docs/TROUBLESHOOTING.md`.

---

## 📦 Phase 1 — Chuẩn bị môi trường local (10 phút)

- [ ] **T1.1** Kiểm tra Python version:
  ```powershell
  python --version
  ```
  Yêu cầu: **3.11 hoặc 3.12** (đừng dùng 3.13 vì một số package chưa support)

- [ ] **T1.2** Kiểm tra Git đã cài:
  ```powershell
  git --version
  ```

- [ ] **T1.3** Tạo folder làm việc:
  ```powershell
  cd C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test
  ```

- [ ] **T1.4** Copy toàn bộ file trong package này vào `build_test\` (thay các file .ipynb cũ)

- [ ] **T1.5** Verify cấu trúc file:
  ```powershell
  dir /b
  ```
  Kỳ vọng thấy: `dashboard.py`, `lib/`, `pages/`, `scripts/`, `.github/`, `.streamlit/`, `requirements*.txt`, `README.md`, ...

---

## 🐍 Phase 2 — Setup Python virtualenv (5 phút)

- [ ] **T2.1** Tạo virtualenv:
  ```powershell
  python -m venv .venv
  ```

- [ ] **T2.2** Activate:
  ```powershell
  .venv\Scripts\activate
  ```
  Prompt phải hiển thị `(.venv)` ở đầu.

- [ ] **T2.3** Upgrade pip:
  ```powershell
  python -m pip install --upgrade pip
  ```

- [ ] **T2.4** Cài deps (cả 2 requirements để local test được cả build script và dashboard):
  ```powershell
  pip install -r requirements.txt -r requirements-actions.txt
  ```
  Chờ ~2-3 phút. Nếu lỗi `psycopg2-binary` không cài được trên Windows → thử:
  ```powershell
  pip install psycopg2-binary --only-binary :all:
  ```

- [ ] **T2.5** Verify cài đặt:
  ```powershell
  python -c "import streamlit, pandas, plotly, sqlalchemy, duckdb; print('OK')"
  ```
  Phải in `OK`.

---

## 🔐 Phase 3 — Tạo file secrets local (3 phút)

- [ ] **T3.1** Tạo file `.env` (KHÔNG commit git):
  ```powershell
  notepad .env
  ```
  Nội dung:
  ```
  SUPABASE_DB_URI=postgresql://postgres.xxx:PASSWORD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres
  GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
  GOOGLE_CLIENT_SECRET=xxx
  GOOGLE_REFRESH_TOKEN=xxx
  ```
  → Copy giá trị từ repo `daily-report-affina` cũ (file `.env` hoặc từ GitHub Secrets của repo đó).

- [ ] **T3.2** Tạo `.streamlit/secrets.toml`:
  ```powershell
  copy .streamlit\secrets.toml.example .streamlit\secrets.toml
  notepad .streamlit\secrets.toml
  ```
  Điền `SUPABASE_DB_URI` (chỉ cần biến này cho dashboard).

- [ ] **T3.3** Verify `.gitignore` đang chặn `.env` và `secrets.toml`:
  ```powershell
  git check-ignore -v .env .streamlit\secrets.toml
  ```
  Phải trả về `.gitignore:XX:.env` và `.gitignore:XX:secrets.toml`.

---

## 🧪 Phase 4 — Test build script local (10 phút)

- [ ] **T4.1** Chạy build script:
  ```powershell
  python scripts/build_dashboard_data.py
  ```
  Kỳ vọng log ra tương tự:
  ```
  [2026-07-15 10:00:00] BUILD DASHBOARD DATA — START
  [2026-07-15 10:00:02] [Step 1] Đã auth Google Drive
  [2026-07-15 10:00:03] [Step 2] Đang tải data từ Google Drive...
  ...
  [2026-07-15 10:03:00] BUILD DASHBOARD DATA — DONE in 180.0s
    Rows: 45,231
    Core=12,345 | Neo=8,765 | TSA=24,121
  ```

- [ ] **T4.2** Nếu lỗi `HttpError 403: refresh token expired`:
  → Chạy lại `get_refresh_token.py` từ repo cũ, cập nhật `.env` và GitHub Secrets.

- [ ] **T4.3** Nếu lỗi `psycopg2.OperationalError: connection timeout`:
  → Supabase free đôi khi cần vài giây wake-up. Chạy lại lần 2.

- [ ] **T4.4** Verify data đã lên Supabase — vào https://supabase.com → SQL Editor → chạy:
  ```sql
  SELECT COUNT(*), MIN("Ngày thanh toán"), MAX("Ngày thanh toán")
  FROM dashboard_master_data;

  SELECT * FROM dashboard_meta ORDER BY id DESC LIMIT 5;
  ```

---

## 🖥️ Phase 5 — Test dashboard local (5 phút)

- [ ] **T5.1** Chạy Streamlit:
  ```powershell
  streamlit run dashboard.py
  ```

- [ ] **T5.2** Browser tự mở `http://localhost:8501`. Nếu không, mở thủ công.

- [ ] **T5.3** Verify từng trang:
  - [ ] 🏠 Tổng quan: 7 KPI hiện đúng, line chart + donut render
  - [ ] 📊 Kênh & Sản phẩm: sunburst zoom được, treemap show
  - [ ] 👥 Đội ngũ Sales: sankey render, scatter có nhiều điểm
  - [ ] 📅 Phân tích thời gian: YoY bar + heatmap
  - [ ] 🔍 Chi tiết & Filter: table hiển thị, download CSV thử được

- [ ] **T5.4** Test filter:
  - Kéo date range → charts update
  - Bỏ chọn `Neo` trong Source → tất cả chart chỉ còn Core + TSA
  - Nhấn `🔄 Refresh Data` → thấy "Đang tải data từ Supabase..."

- [ ] **T5.5** Stop Streamlit: `Ctrl+C` ở terminal

---

## 🐙 Phase 6 — Push lên GitHub (5 phút)

- [ ] **T6.1** Tạo repo mới trên GitHub:
  - Truy cập https://github.com/new
  - Owner: `VietAnh954`
  - Repo name: `affina-dashboard`
  - **Visibility: Public** (để dùng Streamlit Cloud free)
  - Bỏ chọn "Initialize with README" (mình đã có sẵn)
  - Click "Create repository"

- [ ] **T6.2** Init git local:
  ```powershell
  cd C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test
  git init
  git add .
  git status
  ```
  Verify: `.env` và `secrets.toml` **không** xuất hiện trong `git status`.

- [ ] **T6.3** First commit:
  ```powershell
  git commit -m "feat: initial dashboard + auto build pipeline"
  git branch -M main
  git remote add origin https://github.com/VietAnh954/affina-dashboard.git
  git push -u origin main
  ```

- [ ] **T6.4** Verify trên browser: `https://github.com/VietAnh954/affina-dashboard`

---

## 🔑 Phase 7 — Setup GitHub Secrets (3 phút)

Xem chi tiết trong `docs/SETUP_GITHUB_ACTIONS.md`.

- [ ] **T7.1** Vào repo Settings → Secrets and variables → Actions → New repository secret

- [ ] **T7.2** Add 4 secrets (copy giá trị từ `.env` local):
  - [ ] `SUPABASE_DB_URI`
  - [ ] `GOOGLE_CLIENT_ID`
  - [ ] `GOOGLE_CLIENT_SECRET`
  - [ ] `GOOGLE_REFRESH_TOKEN`

- [ ] **T7.3** Test workflow thủ công:
  - Actions tab → "Build Dashboard Data" → Run workflow → chọn `main` → Run workflow
  - Chờ ~3-5 phút → click vào run → xem log
  - Verify final log: `BUILD DASHBOARD DATA — DONE in X.Xs`

---

## ☁️ Phase 8 — Deploy Streamlit Cloud (10 phút)

Xem chi tiết trong `docs/SETUP_STREAMLIT_CLOUD.md`.

- [ ] **T8.1** Truy cập https://share.streamlit.io/ → Sign in with GitHub

- [ ] **T8.2** Click "Create app" → "Deploy a public app from GitHub"

- [ ] **T8.3** Điền form:
  - Repository: `VietAnh954/affina-dashboard`
  - Branch: `main`
  - Main file path: `dashboard.py`
  - App URL subdomain: `affina-dashboard` (hoặc tên khác)

- [ ] **T8.4** Click "Advanced settings" → Secrets → paste:
  ```toml
  SUPABASE_DB_URI = "postgresql://postgres.xxx:PASSWORD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
  ```

- [ ] **T8.5** Click **Deploy!** — chờ 3-5 phút

- [ ] **T8.6** App live tại `https://affina-dashboard.streamlit.app`

- [ ] **T8.7** Verify từng trang hoạt động y hệt local

---

## 🔄 Phase 9 — Verify auto-schedule (2 phút)

- [ ] **T9.1** Vào GitHub repo → Actions → "Build Dashboard Data"
- [ ] **T9.2** Verify text "Next run" hiển thị thời gian cron tiếp theo (~10:00 VN mai)
- [ ] **T9.3** Sáng hôm sau (10:00-10:30 VN), refresh lại Actions, xem run mới đã chạy
- [ ] **T9.4** Mở dashboard → sidebar → verify "Cập nhật gần nhất" là hôm nay
- [ ] **T9.5** (Optional) Click "🔄 Refresh Data" → thấy loading spinner rồi UI reload

---

## 📢 Phase 10 — Share cho team (1 phút)

- [ ] **T10.1** Copy link `https://affina-dashboard.streamlit.app`

- [ ] **T10.2** Share qua Zalo/Slack/Email cho team:
  > Chào cả team, dashboard theo dõi doanh số CORE/NEO/TSA real-time đây:
  > https://affina-dashboard.streamlit.app
  >
  > Data tự cập nhật mỗi ngày 10h sáng. Có 5 trang phân tích chi tiết. Cứ vào xem là ra data mới nhất, không cần login.

- [ ] **T10.3** (Optional) Bookmark link trên trình duyệt team

---

## 🎓 Phase 11 — Monitor & Maintain (ongoing)

- [ ] **T11.1** Hàng tuần: kiểm tra Actions tab, xem 7 job cuối có green ✅ hết không
- [ ] **T11.2** Hàng tháng: check Supabase storage (Settings → Database → Storage usage). Free tier 500MB. Nếu gần đầy → xóa bớt bảng `dashboard_meta` cũ:
  ```sql
  DELETE FROM dashboard_meta
  WHERE id NOT IN (SELECT id FROM dashboard_meta ORDER BY id DESC LIMIT 100);
  ```
- [ ] **T11.3** Nếu team feedback cần thêm chart → sửa file trong `pages/`, push main → Streamlit auto-redeploy

---

## 🚨 Nếu bí quá, xem docs theo thứ tự

1. `docs/TROUBLESHOOTING.md` — 90% lỗi thường gặp đã có trong này
2. `docs/SETUP_GITHUB_ACTIONS.md` — chi tiết setup Actions
3. `docs/SETUP_STREAMLIT_CLOUD.md` — chi tiết deploy Streamlit
4. `AGENT_INSTRUCTIONS.md` — nếu là AI Agent đọc file này
5. `ARCHITECTURE.md` — hiểu why + how
6. `DASHBOARD_DESIGN.md` — hiểu từng chart

---

## ✅ Final checklist trước khi bàn giao

- [ ] Local build script chạy được, không error
- [ ] Local dashboard hiển thị 5 trang đầy đủ
- [ ] Code đã push lên GitHub, workflow chạy được ít nhất 1 lần thủ công (green ✅)
- [ ] Streamlit app đã live, share được cho người khác truy cập
- [ ] Data trong bảng Supabase có > 0 dòng
- [ ] `dashboard_meta` có row mới nhất là hôm nay
- [ ] Đã share link cho VietAnh + team
