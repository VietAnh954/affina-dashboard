# 🤖 AGENT INSTRUCTIONS — Đọc file này ĐẦU TIÊN

> **Mục tiêu**: Bạn (AI Agent) sẽ giúp VietAnh triển khai một dashboard real-time trên nền tảng Streamlit Community Cloud, đọc data từ Supabase, tự động cập nhật hàng ngày lúc 10h sáng VN qua GitHub Actions. Toàn bộ MIỄN PHÍ.

---

## 📋 CONTEXT — Những gì VietAnh đã có sẵn

VietAnh làm việc tại **Affina** (công ty bảo hiểm), phụ trách reporting/data ops. Anh ấy đã có:

1. ✅ **Supabase (PostgreSQL free tier)** với 3 bảng:
   - `qd1` — bảng quy đổi (tỉ lệ hoa hồng, rate_bonus, Affina_rate_bonus, …)
   - `ds_nhan_su_affina` — danh sách nhân sự sale (Code, Họ tên, Chức danh, Channel, BDM, BDD, …)
   - `union_all_data_cap_don` — hợp đồng đã cấp đơn (7 loại BH: BHSK, BHXM, BHYT, BHOTO, BHDL, TNDS, BHRR)

2. ✅ **GitHub repo private**: `VietAnh954/daily-report-affina` (nếu chưa có repo dashboard, tạo mới; xem step 1)

3. ✅ **4 GitHub Secrets đã tồn tại** (không cần tạo lại):
   - `SUPABASE_DB_URI` — connection string PostgreSQL
   - `GOOGLE_CLIENT_ID` — OAuth Client ID
   - `GOOGLE_CLIENT_SECRET` — OAuth Client Secret
   - `GOOGLE_REFRESH_TOKEN` — Refresh Token đã lấy từ script `get_refresh_token.py`

4. ✅ **Google Sheet ID (Cấp đơn)**: `1qc_QhrvpoLLp6w9RkGBEkm8qBO49GJE8oMlwkCdJOsk`

5. ✅ **Google Drive files**:
   - `DSNS CTV sale Affina NEW - HR NHẬP.xlsx` (folder `Data` hoặc `Nhân sự sales`)
   - `26_02_04_sửa ngày_quy_doi_all.xlsx` (folder `Data`)

6. ✅ Một job GitHub Actions khác đang chạy hàng ngày 17:00 VN (report AN/LOAN) — **KHÔNG được đụng vào**.

---

## 🎯 KIẾN TRÚC ĐÍCH (đọc kỹ)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      GitHub Actions (cron 10:00 VN)                 │
│                    Cron:  '0 3 * * *'   (UTC = VN - 7)              │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ 1x/ngày
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  scripts/build_dashboard_data.py                                    │
│  ─────────────────────────────────                                  │
│  1. Kết nối Google Drive bằng OAuth Refresh Token                   │
│  2. Tải: Google Sheet Cấp đơn + 2 file Excel (DSNS + Quy đổi)       │
│  3. Clean data (giữ NGUYÊN logic từ 3 notebook gốc)                 │
│  4. Push 3 bảng nguồn lên Supabase (qd1, ds_nhan_su_affina,         │
│     union_all_data_cap_don) — replace                                │
│  5. Chạy DuckDB 3 query (CORE, NEO, TSA) — logic từ File 3 gốc      │
│  6. Combine + Subtotal → df_master                                  │
│  7. Push df_master lên bảng MỚI: `dashboard_master_data`            │
│  8. Push metadata (last_update timestamp, row count) →              │
│     bảng `dashboard_meta`                                            │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ ghi
                                 ▼
                    ┌────────────────────────┐
                    │      Supabase          │
                    │  (PostgreSQL FREE)     │
                    │                        │
                    │  dashboard_master_data │ ◄──┐
                    │  dashboard_meta        │    │
                    └────────────────────────┘    │
                                                  │ đọc real-time
                                                  │ (cache TTL 5 phút)
                    ┌─────────────────────────────┴────────────┐
                    │   Streamlit Cloud (FREE public URL)      │
                    │   https://affina-dashboard.streamlit.app │
                    │                                          │
                    │   dashboard.py  (multi-page)             │
                    │   ├── 🏠 Tổng quan (KPI + trend)         │
                    │   ├── 📊 Kênh & Sản phẩm                 │
                    │   ├── 👥 Đội ngũ Sales                   │
                    │   ├── 📅 Phân tích theo thời gian        │
                    │   └── 🔍 Chi tiết & Filter                │
                    └─────────────────┬────────────────────────┘
                                      │
                                      ▼
                            👥 Người xem (share link)
                            Refresh = data mới nhất
```

---

## ✅ TASK LIST — Làm theo đúng thứ tự

### Phase 1 — Chuẩn bị (5 phút)

- [ ] **T1.1** Đọc file `README.md` để hiểu tổng quan
- [ ] **T1.2** Đọc file `ARCHITECTURE.md` để hiểu kiến trúc
- [ ] **T1.3** Đọc file `DASHBOARD_DESIGN.md` để hiểu design từng chart
- [ ] **T1.4** Kiểm tra folder local `C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test`
      → chuyển toàn bộ package này vào đó

### Phase 2 — Cấu trúc project (2 phút)

- [ ] **T2.1** Verify cấu trúc file:
  ```
  build_test/
  ├── .github/workflows/build_dashboard.yml
  ├── .streamlit/
  │   ├── config.toml
  │   └── secrets.toml.example
  ├── scripts/
  │   └── build_dashboard_data.py         ← chạy hàng ngày trên GitHub Actions
  ├── pages/
  │   ├── 2_📊_Kenh_va_San_pham.py
  │   ├── 3_👥_Doi_ngu_Sales.py
  │   ├── 4_📅_Phan_tich_thoi_gian.py
  │   └── 5_🔍_Chi_tiet_va_Filter.py
  ├── dashboard.py                        ← trang chủ Streamlit
  ├── requirements.txt
  ├── requirements-actions.txt            ← deps riêng cho GitHub Actions
  ├── .gitignore
  ├── README.md
  ├── AGENT_INSTRUCTIONS.md               ← file này
  ├── ARCHITECTURE.md
  ├── DASHBOARD_DESIGN.md
  ├── TASKLIST.md
  └── docs/
      ├── SETUP_STREAMLIT_CLOUD.md
      ├── SETUP_GITHUB_ACTIONS.md
      └── TROUBLESHOOTING.md
  ```

### Phase 3 — Test local build script (10 phút)

- [ ] **T3.1** Cài Python 3.12 (nếu chưa có)
- [ ] **T3.2** Ở terminal, cd vào `build_test`
- [ ] **T3.3** Tạo virtualenv:
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements-actions.txt
  ```
- [ ] **T3.4** Tạo file `.env` (KHÔNG commit lên git) với 4 biến:
  ```
  SUPABASE_DB_URI=postgresql://...
  GOOGLE_CLIENT_ID=...
  GOOGLE_CLIENT_SECRET=...
  GOOGLE_REFRESH_TOKEN=...
  ```
  → Lấy giá trị từ file `.env` cũ của repo `daily-report-affina`
- [ ] **T3.5** Chạy thử `python scripts/build_dashboard_data.py`
  - Kỳ vọng: log ra "Đã push X dòng vào dashboard_master_data"
  - Nếu lỗi → xem `docs/TROUBLESHOOTING.md`
- [ ] **T3.6** Vào Supabase Studio → SQL Editor → chạy:
  ```sql
  SELECT COUNT(*) FROM dashboard_master_data;
  SELECT * FROM dashboard_meta ORDER BY updated_at DESC LIMIT 1;
  ```
  → Phải có data.

### Phase 4 — Test dashboard local (5 phút)

- [ ] **T4.1** Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
      và điền `SUPABASE_DB_URI`
- [ ] **T4.2** Chạy `streamlit run dashboard.py`
- [ ] **T4.3** Mở browser `http://localhost:8501`
      → xem 5 trang: Tổng quan, Kênh, Đội ngũ, Thời gian, Chi tiết
- [ ] **T4.4** Kiểm tra chart hiển thị đúng, filter hoạt động

### Phase 5 — Push lên GitHub (5 phút)

- [ ] **T5.1** Tạo repo GitHub MỚI (Public hoặc Private đều được):
      Recommended: `VietAnh954/affina-dashboard` — chọn **Public**
      (Streamlit Community Cloud FREE cho public repo)
- [ ] **T5.2** Init git:
  ```powershell
  cd C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test
  git init
  git add .
  git commit -m "feat: initial dashboard + auto build pipeline"
  git branch -M main
  git remote add origin https://github.com/VietAnh954/affina-dashboard.git
  git push -u origin main
  ```
- [ ] **T5.3** Vào repo Settings → Secrets and variables → Actions → thêm 4 secrets:
      `SUPABASE_DB_URI`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
- [ ] **T5.4** Test workflow manual:
      Actions → "Build Dashboard Data" → Run workflow → Run workflow
- [ ] **T5.5** Chờ ~3-5 phút, check log green ✅

### Phase 6 — Deploy Streamlit Cloud (10 phút)

- [ ] **T6.1** Truy cập https://share.streamlit.io/
- [ ] **T6.2** Đăng nhập bằng tài khoản GitHub (dùng `VietAnh954`)
- [ ] **T6.3** Click "Create app" → "Deploy a public app from GitHub"
- [ ] **T6.4** Nhập:
      - Repository: `VietAnh954/affina-dashboard`
      - Branch: `main`
      - Main file path: `dashboard.py`
      - App URL (subdomain): `affina-dashboard` (hoặc tên khác)
- [ ] **T6.5** Click "Advanced settings" → Secrets → paste:
  ```toml
  SUPABASE_DB_URI = "postgresql://..."
  ```
- [ ] **T6.6** Click **Deploy!** — chờ ~5 phút
- [ ] **T6.7** App live tại `https://affina-dashboard.streamlit.app`

### Phase 7 — Verify auto-schedule (2 phút)

- [ ] **T7.1** Vào GitHub repo → Actions → xem `Build Dashboard Data`
- [ ] **T7.2** Check next scheduled run (hiển thị bên cạnh)
- [ ] **T7.3** Đến 10h sáng hôm sau, xem log → phải chạy thành công
- [ ] **T7.4** Vào dashboard, click nút "🔄 Refresh Data" ở sidebar → thấy timestamp mới

### Phase 8 — Share cho team (1 phút)

- [ ] **T8.1** Copy link `https://affina-dashboard.streamlit.app`
- [ ] **T8.2** Gửi cho team qua Slack/Zalo — bất kỳ ai có link đều xem được

---

## 🔧 QUY TẮC LÀM VIỆC CHO AGENT

1. **KHÔNG được đụng vào** repo `daily-report-affina` — repo đó đang chạy production job 17h.
2. **KHÔNG được xóa/sửa** 3 bảng gốc `qd1`, `ds_nhan_su_affina`, `union_all_data_cap_don` (job 17h dùng chung).
3. Bảng của dashboard là bảng MỚI, tên: `dashboard_master_data` và `dashboard_meta` — hoàn toàn độc lập.
4. **Giờ chạy**: 10:00 VN = `0 3 * * *` (UTC). Nếu VietAnh có job khác trong repo cùng, phải chọn thời điểm không xung đột.
5. **Ngôn ngữ chú thích** trong code: giữ tiếng Việt cho phần comment nghiệp vụ (VietAnh dễ đọc lại), tiếng Anh cho phần technical.
6. Nếu có lỗi khi chạy, xem `docs/TROUBLESHOOTING.md` trước khi tự chế cách sửa mới.
7. Nếu VietAnh hỏi "tại sao dùng Streamlit chứ không phải Looker/Metabase" → trả lời có trong `docs/PLATFORM_COMPARISON.md`.

---

## 🚨 NHỮNG LỖI THƯỜNG GẶP (đọc kỹ trước khi chạy)

| # | Lỗi | Nguyên nhân | Fix |
|---|---|---|---|
| 1 | `psycopg2.OperationalError: connection timeout` | Supabase free tier có sleep sau vài phút không dùng | Retry 2-3 lần, hoặc dùng `pool_pre_ping=True` |
| 2 | `HttpError 403: refresh token expired` | User đã revoke access | Chạy lại `get_refresh_token.py` (script cũ của repo `daily-report-affina`) |
| 3 | `st.secrets["SUPABASE_DB_URI"]: KeyError` | Chưa thêm secret trên Streamlit Cloud | Vào app settings → Secrets → paste `SUPABASE_DB_URI = "..."` |
| 4 | Streamlit Cloud app "sleeps" sau 7 ngày | Free tier limit | Chỉ cần ai đó truy cập link → tự động wake up trong ~30s |
| 5 | GitHub Actions cron chậm 5-15 phút | Hàng đợi free tier | Hành vi bình thường, không phải bug |
| 6 | Charts không hiển thị số 0 khi filter rỗng | Data cột NULL | Đã handle trong `dashboard.py` — nếu vẫn lỗi, xem `TROUBLESHOOTING.md` |

---

## ✅ CHECKLIST FINAL — TRƯỚC KHI BÀN GIAO CHO VIETANH

- [ ] Workflow GitHub Actions đã chạy thành công ít nhất 1 lần (green check)
- [ ] Supabase bảng `dashboard_master_data` có > 0 row
- [ ] Supabase bảng `dashboard_meta` có row mới nhất với timestamp hôm nay
- [ ] Streamlit app live tại URL public
- [ ] Cả 5 trang dashboard hiển thị chart, không có error
- [ ] Filter sidebar hoạt động (chọn khoảng thời gian → chart update)
- [ ] Nút refresh sidebar hoạt động
- [ ] Đã test share link cho 1 người khác không login GitHub — xem được

---

**Nếu tất cả checklist ✅ → nhắn cho VietAnh:**

> Dashboard đã deploy xong tại `https://affina-dashboard.streamlit.app`. Data tự cập nhật mỗi ngày 10h sáng. Anh chia sẻ link cho team để xem. Mọi thắng chậc xem docs/ hoặc pings tôi.

---

Chúc bạn — Agent — làm việc thuận lợi. Nếu gặp vấn đề không có trong docs, đọc kỹ log lỗi trước khi đoán, và ưu tiên bảo toàn 3 bảng dùng chung với job 17h.
