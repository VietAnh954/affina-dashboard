# 🏛️ ARCHITECTURE — Kiến trúc hệ thống Dashboard

## 1. Vấn đề & Yêu cầu

### 1.1 Yêu cầu từ VietAnh

| # | Yêu cầu | Priority |
|---|---|---|
| 1 | Dashboard cho 3 file notebook (`.ipynb`) | Must |
| 2 | Nhiều biểu đồ đa dạng, thể hiện các trường dữ liệu đặc trưng | Must |
| 3 | **Code-first**, KHÔNG kéo thả | Must |
| 4 | Tự động chạy hàng ngày 10h sáng VN | Must |
| 5 | Real-time — refresh là thấy data mới | Must |
| 6 | Có link share được cho bất kỳ ai | Must |
| 7 | **MIỄN PHÍ hoàn toàn** | Must |

### 1.2 Ràng buộc kỹ thuật hiện tại

- Data gốc ở Google Sheet + 2 file Excel trên Google Drive
- Đã có OAuth Refresh Token, Supabase free, GitHub Actions
- 3 notebooks có logic pipeline **IDENTICAL**, chỉ khác WHERE clause (time filter) và output

---

## 2. Lựa chọn nền tảng (Platform Decision)

### 2.1 Bảng so sánh chi tiết

| Platform | Code-first | Real-time | Share URL | Free | Auto-refresh | Setup | Kết luận |
|---|---|---|---|---|---|---|---|
| **Streamlit Cloud** | ✅ Pure Python | ✅ Cache TTL | ✅ Public | ✅ Có | ✅ | Dễ (5 phút) | **⭐ CHỌN** |
| Looker Studio | ❌ Drag & drop | ✅ | ✅ | ✅ | ✅ | Dễ | Bị loại — drag drop |
| Metabase (self-host) | ⚠️ Mostly UI | ✅ | ⚠️ Cần server | ⚠️ Chỉ tools free | ✅ | Trung bình | Cần host |
| Grafana (self-host) | ⚠️ SQL + UI | ✅ | ✅ | ⚠️ Cần host | ✅ | Khó | Overkill |
| Dash (Plotly) | ✅ Pure Python | ✅ | ⚠️ Cần host | ⚠️ Free host giới hạn | ✅ | Trung bình | Giống Streamlit nhưng deploy khó hơn |
| Panel/Voila | ✅ Python | ✅ | ⚠️ | ⚠️ | ✅ | Khó | Không có free hosting tốt |
| Apache Superset | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | Rất khó | Enterprise-grade, quá phức tạp |
| Power BI Free | ❌ | ✅ | ❌ Cần login | ⚠️ | ✅ | Dễ | Không share public được |
| Tableau Public | ❌ | ⚠️ Manual refresh | ✅ | ✅ | ❌ | Dễ | Không auto-refresh |

### 2.2 Vì sao chọn Streamlit Community Cloud

**Ưu điểm:**
1. ✅ **100% Python code** — dựng chart bằng Plotly/Altair, không kéo thả
2. ✅ **Free forever** cho public repo (Community Cloud)
3. ✅ **Public URL sẵn**: `https://<app-name>.streamlit.app`
4. ✅ **Deploy siêu dễ**: connect GitHub → click Deploy → xong
5. ✅ **Reads Supabase trực tiếp** — không cần rebuild dashboard, refresh là ra data mới
6. ✅ **Multi-page support** natively (folder `pages/`)
7. ✅ **Cache system** (`st.cache_data`) với TTL — cân bằng speed vs freshness
8. ✅ **Widget interactive**: slider, multiselect, date range, download button
9. ✅ **Tài liệu tiếng Việt phong phú**, community lớn
10. ✅ **Không tốn RAM/CPU của VietAnh** — chạy trên infra Streamlit

**Nhược điểm (đã có mitigation):**
- ⚠️ App sleep sau 7 ngày inactive → **wake up 30s khi có visitor**. Team dùng hàng ngày sẽ không bao giờ sleep.
- ⚠️ 1GB RAM limit → **đủ dùng** cho dashboard này (data ~vài chục MB max)

### 2.3 Vì sao KHÔNG chọn Looker Studio

Mặc dù File 3 gốc đã có bước xuất Google Sheet cho Looker Studio, VietAnh nói rõ **"không muốn kéo thả"**. Looker Studio là công cụ drag-and-drop, chart phải config bằng UI. Với người có kỹ năng SQL + Python như VietAnh, Streamlit cho phép:
- Version control chart config qua git
- Reuse component (function trả về chart)
- Custom logic phức tạp (multi-step calculation, conditional formatting) mà Looker khó làm

---

## 3. Kiến trúc dòng dữ liệu

### 3.1 Sơ đồ

```
                  ┌────────────────────────────────────┐
                  │   Google Drive (nguồn gốc)         │
                  │   ─────────────────────             │
                  │   • Google Sheet "Cấp đơn"          │
                  │   • DSNS CTV sale Affina.xlsx       │
                  │   • Quy đổi.xlsx                    │
                  └───────────────┬────────────────────┘
                                  │  OAuth Refresh Token
                                  │  (chạy từ GH Actions)
                                  ▼
      ┌─────────────────────────────────────────────────────────┐
      │  scripts/build_dashboard_data.py                        │
      │  ══════════════════════════════════                     │
      │                                                          │
      │  Step 1: Auth Google Drive API                          │
      │  Step 2: Download Sheet + 2 Excel → memory              │
      │  Step 3: Clean 7 loại BH (BHSK/BHXM/BHYT/…) + join      │
      │          → df_union, df_ns, qd1                         │
      │  Step 4: Push 3 df lên Supabase (replace)               │
      │  Step 5: DuckDB in-memory:                              │
      │            ├─ CORE query  → df_core                     │
      │            ├─ NEO query   → df_neo                      │
      │            └─ TSA query   → df_tsa                      │
      │  Step 6: Combine → df_master (~50-100k rows expected)   │
      │  Step 7: Push df_master → `dashboard_master_data`       │
      │  Step 8: Push metadata → `dashboard_meta`               │
      └───────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼
      ┌─────────────────────────────────────────────────────────┐
      │  Supabase (PostgreSQL FREE tier — 500MB)                │
      │  ═══════════════════════════════════                    │
      │                                                          │
      │  Bảng chung (dùng cả job 17h AN/LOAN):                  │
      │  ├─ qd1                                                 │
      │  ├─ ds_nhan_su_affina                                   │
      │  └─ union_all_data_cap_don                              │
      │                                                          │
      │  Bảng riêng cho Dashboard:                              │
      │  ├─ dashboard_master_data    ← join sẵn CORE+NEO+TSA    │
      │  └─ dashboard_meta            ← last_update, row_count   │
      └───────────────────────────┬─────────────────────────────┘
                                  │
                                  │  psycopg2 (read-only)
                                  │  st.cache_data(ttl=300)
                                  ▼
      ┌─────────────────────────────────────────────────────────┐
      │  Streamlit Cloud (FREE public app)                      │
      │  ═══════════════════════════════                        │
      │                                                          │
      │  URL: https://<app>.streamlit.app                       │
      │                                                          │
      │  Trang chủ: dashboard.py                                │
      │  ├── 🏠 Tổng quan (KPI cards + trend)                   │
      │  Pages:                                                 │
      │  ├── 📊 Kênh & Sản phẩm                                 │
      │  ├── 👥 Đội ngũ Sales (BDM/BDD hierarchy)               │
      │  ├── 📅 Phân tích theo thời gian (YoY, MoM)             │
      │  └── 🔍 Chi tiết & Filter (table + download)             │
      │                                                          │
      │  Sidebar (global filters):                              │
      │  ├─ Date range picker                                   │
      │  ├─ Source (Core/Neo/TSA) multiselect                   │
      │  ├─ Channel multiselect                                 │
      │  ├─ Loại BH multiselect                                 │
      │  └─ 🔄 Refresh Data button (clear cache)                │
      └────────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
                          👥 Team Affina xem
                          (chỉ cần link, không cần login)
```

### 3.2 Timeline hàng ngày

```
17:00 VN   Job cũ (AN/LOAN)          → Cập nhật qd1, ds_nhan_su_affina, union_all_data_cap_don
                                        Xuất 4 file Excel lên Google Drive
                                        Fresh source data ✅

10:00 VN   Job MỚI (Dashboard)       → Đọc lại từ Google Drive (fresh)
(next day)                             Push qd1/ds_nhan_su/union_all (replace)
                                       Chạy CORE+NEO+TSA queries
                                       Push dashboard_master_data
                                       Cập nhật dashboard_meta

10:05+ VN  User mở dashboard         → Streamlit đọc từ Supabase
                                       Cache 5 phút → 1 lần đọc/5phút cho tất cả user
                                       Chart render, ai cũng thấy data 10:00 hôm nay ✅
```

### 3.3 Vì sao KHÔNG chạy queries trực tiếp trên Streamlit?

**Alternative:** để Streamlit tự query Supabase → join → tính CORE/NEO/TSA mỗi lần user mở.

**Vấn đề:**
- Streamlit free có 1GB RAM → không tải nổi 3 bảng gốc + join
- Query time > 20s → user experience xấu
- Nhiều user cùng lúc → Supabase quá tải

**Giải pháp đã chọn:** pre-compute mỗi ngày, dashboard chỉ đọc bảng đã join sẵn → **fast (<2s load)**, ít RAM, chịu được nhiều user.

---

## 4. Data Model — Bảng `dashboard_master_data`

### 4.1 Schema (khoảng 50+ cột, giữ nguyên từ 3 notebook gốc)

| Nhóm | Cột | Type | Ghi chú |
|---|---|---|---|
| **Identity** | `Source` | text | 'Core' / 'Neo' / 'TSA' |
| | `Channel` | text | 'Core Agency', 'Neo', 'H.O', 'TSA', 'RENEW', … |
| **Contract** | `Số hợp đồng` | text | Contract number |
| | `Loại bảo hiểm` | text | 'BHSK'/'BHXM'/'BHYT/BHXH'/'BHOTO'/'BHDL'/'TNDS'/'BHRR' |
| | `Sản phẩm` | text | Product name |
| | `Nhà BH` | text | Insurance partner (Đối tác nhà bảo hiểm) |
| | `Ngày thanh toán` | date | Date of payment (main time axis) |
| | `Ngày bắt đầu` | date | Contract start |
| | `Ngày kết thúc` | date | Contract end |
| **Customer** | `Tên NMBH` | text | Buyer name |
| | `Tên NĐBH` | text | Insured name |
| | `Giới tính NNBH` | text | 'Nam'/'Nữ' |
| | `Quan hệ` | text | Relationship (Vợ, Chồng, Con, …) |
| | `Ngoại trú`, `Nha khoa`, `Thai sản`, `Topup` | text | BHSK add-ons |
| **Sales team** | `Họ tên sale` | text | Salesperson name |
| | `Chức danh` | text | 'CTV', 'BDM', 'BDD', 'BDH', 'TSA' |
| | `QUẢN LÝ CẤP 1 (BDM)` | text | Manager level 1 |
| | `QUẢN LÝ CẤP 2 (BDD)` | text | Manager level 2 |
| | `Quản lý Cấp 3 (BDH)` | text | Manager level 3 |
| **Financial** | `Số tiền thanh toán` | numeric | Payment amount (VNĐ) |
| | `Phí BH (VNĐ)` | numeric | Insurance premium |
| | `Doanh thu trước thuế` | numeric | Pre-tax revenue |
| | `EST_Bonus` | numeric | Estimated bonus |
| | `Affina_Revenue` | numeric | Company revenue |
| | `Thưởng Teamlead` | numeric | Teamlead bonus |
| | `Incentive OVE` | numeric | Extra incentive |
| | `SM_OR`, `SD_OR`, `SM_IO`, `SD_IO` | numeric | Neo-only bonuses |
| | `BDM_bonus`, `BDD_bonus` | numeric | Manager bonuses |
| | `Chi Agency`, `Chi QL` | numeric | Costs |
| | `Budget Neo T6` | numeric | Neo budget |
| **Rate** | `rate_bonus`, `Affina_rate_bonus`, `exchange_core` | numeric | Rates |
| **Meta** | `_ingested_at` | timestamptz | Khi dòng này được insert (tự thêm) |

### 4.2 Bảng `dashboard_meta`

```sql
CREATE TABLE dashboard_meta (
    id           SERIAL PRIMARY KEY,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    row_count    INTEGER,
    core_count   INTEGER,
    neo_count    INTEGER,
    tsa_count    INTEGER,
    date_min     DATE,
    date_max     DATE,
    duration_sec NUMERIC,
    status       TEXT,      -- 'success' / 'error'
    error_msg    TEXT
);
```

Streamlit query `SELECT * FROM dashboard_meta ORDER BY id DESC LIMIT 1` để hiện "Last updated" ở góc dashboard.

---

## 5. Bảo mật & Rủi ro

### 5.1 Public app + Supabase read-only

- Dashboard app public → **ai có link đều xem được**. Đây là mong muốn của VietAnh.
- Streamlit connection dùng cùng `SUPABASE_DB_URI` với Actions → về mặt kỹ thuật app có quyền read/write.
- **Mitigation**: code chỉ dùng `SELECT`. Có thể siết chặt thêm bằng cách tạo 1 Postgres user riêng cho dashboard với chỉ quyền `SELECT` trên 2 bảng dashboard_*.
  → **Ghi vào TODO khi có thời gian** (không blocking).

### 5.2 Rate limit Supabase free

- Free tier: 500MB storage, connection pool ~50, egress 5GB/tháng
- Với cache TTL 5 phút → mỗi 5 phút mới có 1 lần query DB → an toàn kể cả 100 concurrent users

### 5.3 Streamlit Cloud limit

- 1 GB RAM per app → check `df` size trước khi ship
- 1 CPU core → không dùng cho heavy compute
- Community Cloud limit: 1 workspace/user, unlimited apps

### 5.4 Refresh Token expire

- OAuth Refresh Token không expire nếu app ở chế độ Testing và user không revoke
- Nếu revoke → chạy lại `get_refresh_token.py` (đã có trong repo `daily-report-affina`)

---

## 6. Extensibility (nếu VietAnh muốn mở rộng)

| Nếu muốn... | Làm gì |
|---|---|
| Thêm 1 chart mới | Sửa file trong `pages/` — 5-10 dòng |
| Thêm 1 filter | Sửa sidebar trong `dashboard.py` |
| Thêm 1 KPI | Sửa function `render_kpi_cards()` |
| Chạy 2 lần/ngày (10h + 20h) | Sửa cron trong `.github/workflows/build_dashboard.yml`:<br>`- cron: '0 3 * * *'`<br>`- cron: '0 13 * * *'` |
| Có sub-domain riêng (`dashboard.affina.vn`) | Streamlit Cloud paid tier ($20/tháng) HOẶC deploy qua Vercel/Fly.io |
| Chuyển sang Metabase | Bảng `dashboard_master_data` đã ready — chỉ cần connect Metabase vào Supabase |
| Chuyển sang Looker Studio | Vẫn giữ được logic — dùng Google Sheets connector cho bảng đã pre-computed |

---

## 7. Kết luận

Kiến trúc này **tối ưu 3 chiều**:
- **Chi phí**: $0 (GH Actions free + Supabase free + Streamlit Cloud free)
- **Hiệu năng**: pre-compute daily → dashboard load <2s
- **Bảo trì**: Python + SQL, cùng ngôn ngữ VietAnh đang dùng, dễ mở rộng

Đọc tiếp `DASHBOARD_DESIGN.md` để xem chi tiết từng chart trong dashboard.
