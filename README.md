# 🏢 Affina Sales Dashboard

Real-time dashboard cho reports CORE + NEO + TSA của Affina Sales. Data từ Google Sheet + Excel, xử lý qua GitHub Actions, lưu Supabase, hiển thị trên Streamlit Cloud.

**Live URL**: `https://affina-dashboard.streamlit.app` (sau khi deploy)

---

## ⚡ TL;DR

| | |
|---|---|
| **Platform** | Streamlit Community Cloud (Free) |
| **Backend** | Supabase PostgreSQL (Free tier) |
| **ETL** | GitHub Actions cron 10:00 VN mỗi ngày |
| **Cost** | **$0** (miễn phí hoàn toàn) |
| **Data update** | Hàng ngày 10:00 VN |
| **Dashboard cache** | 5 phút TTL (refresh button để clear) |
| **Share** | Link public, ai có link đều xem được |

---

## 🚀 Quick start

### 1. Chuẩn bị

- Python 3.12+
- Tài khoản GitHub (đã có: `VietAnh954`)
- Tài khoản Supabase (đã có, cùng credentials với job daily-report-affina)
- 4 GitHub Secrets đã setup ở repo `daily-report-affina`, có thể reuse

### 2. Chạy local test (5 phút)

```powershell
# 1. Vào folder
cd C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test

# 2. Tạo virtualenv
python -m venv .venv
.venv\Scripts\activate

# 3. Cài đặt cho local dev (cả 2 requirements)
pip install -r requirements.txt -r requirements-actions.txt

# 4. Tạo file .env với 4 biến (copy từ repo daily-report-affina cũ)
notepad .env
```

`.env`:
```
SUPABASE_DB_URI=postgresql://...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

```powershell
# 5. Chạy thử build script
python scripts/build_dashboard_data.py

# 6. Nếu OK, copy secrets template và chạy dashboard
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Sửa file secrets.toml điền SUPABASE_DB_URI

streamlit run dashboard.py
```

Mở `http://localhost:8501` để xem dashboard.

### 3. Deploy lên GitHub + Streamlit Cloud

Xem chi tiết trong:
- `docs/SETUP_GITHUB_ACTIONS.md`
- `docs/SETUP_STREAMLIT_CLOUD.md`

---

## 📁 Cấu trúc project

```
build_test/
├── dashboard.py                             ← Trang chủ Streamlit
├── pages/                                   ← Multi-page app (auto-detect)
│   ├── 2_📊_Kenh_va_San_pham.py
│   ├── 3_👥_Doi_ngu_Sales.py
│   ├── 4_📅_Phan_tich_thoi_gian.py
│   └── 5_🔍_Chi_tiet_va_Filter.py
├── lib/                                     ← Shared utilities
│   ├── __init__.py
│   └── data.py                              ← Load data, filters, formatting
├── scripts/
│   └── build_dashboard_data.py              ← ETL chạy hàng ngày
├── .github/workflows/
│   └── build_dashboard.yml                  ← Cron 10:00 VN
├── .streamlit/
│   ├── config.toml                          ← Theme + server
│   └── secrets.toml.example                 ← Template secrets
├── docs/
│   ├── SETUP_STREAMLIT_CLOUD.md
│   ├── SETUP_GITHUB_ACTIONS.md
│   ├── TROUBLESHOOTING.md
│   └── PLATFORM_COMPARISON.md
├── requirements.txt                         ← Deps Streamlit Cloud
├── requirements-actions.txt                 ← Deps GitHub Actions
├── .gitignore
├── AGENT_INSTRUCTIONS.md                    ← ⭐ File agent đọc đầu tiên
├── ARCHITECTURE.md                          ← Kiến trúc chi tiết
├── DASHBOARD_DESIGN.md                      ← Design từng chart
├── TASKLIST.md                              ← Checklist implement
└── README.md                                ← File này
```

---

## 🎯 Dashboard có gì?

### Trang 1 — 🏠 Tổng quan
- 7 KPI cards (doanh thu, phí BH, số HĐ, Affina revenue, EST bonus, sale active, AVG DT/HĐ)
- Line chart doanh thu theo tháng, tách Source (Core/Neo/TSA)
- Donut chart cơ cấu doanh thu
- 3 sparklines 30 ngày gần nhất
- Top 10 Sale + Top 10 Nhà BH

### Trang 2 — 📊 Kênh & Sản phẩm
- Sunburst 4 cấp: Source → Channel → Loại BH → Sản phẩm
- Bar chart doanh thu theo Channel
- Pie chart cơ cấu Loại bảo hiểm
- Treemap Nhà BH × Loại BH
- Grouped bar top 15 sản phẩm
- BHSK add-ons breakdown (Ngoại trú, Nha khoa, Thai sản, Topup)

### Trang 3 — 👥 Đội ngũ Sales
- Top 20 salesperson
- BDM/BDD performance
- Sankey diagram: CTV → BDM → BDD flow
- Scatter: Số HĐ × Doanh thu (star finder)
- Full detail table + download CSV

### Trang 4 — 📅 Phân tích thời gian
- YoY comparison (bar 12 tháng × 3 năm)
- MoM combo chart (bar + growth line)
- Heatmap ngày × tuần
- Cumulative revenue area
- Contract expiry (HĐ sắp hết hạn — dùng cho tái tục)

### Trang 5 — 🔍 Chi tiết & Filter
- Advanced filters (text search, range slider, multiselect)
- Interactive datatable với column config
- Download CSV + Excel
- Statistical summary

---

## 🔄 Data flow

```
Google Drive (Sheet Cấp đơn + 2 Excel)
        ↓  [OAuth Refresh Token]
GitHub Actions (10:00 VN daily)
        ↓  [build_dashboard_data.py]
        ↓  Clean + JOIN + DuckDB queries
Supabase PostgreSQL
        ↓  [psycopg2 read-only, cache TTL 5 phút]
Streamlit Cloud (public URL)
        ↓
👥 Team Affina (share link)
```

Xem `ARCHITECTURE.md` để hiểu chi tiết.

---

## 🔒 Bảo mật

- Dashboard là **public** — bất kỳ ai có link đều xem được (đúng theo yêu cầu của VietAnh)
- Data trong Supabase — connection dùng service credentials, không expose ra client
- Nếu muốn siết chặt: tạo Postgres user riêng cho dashboard chỉ có quyền SELECT trên 2 bảng `dashboard_*`
- Refresh Token OAuth Google Drive: chỉ dùng ở GitHub Actions, không bao giờ đến Streamlit

---

## 🧭 FAQ

**Q: Streamlit Cloud có thực sự miễn phí không?**
A: Có, Community Cloud free forever cho public repo. Giới hạn 1GB RAM, 1 CPU per app. Đủ dùng cho ~50k rows.

**Q: Dashboard bị "app sleep" là gì?**
A: Nếu 7 ngày liên tiếp không ai truy cập, Streamlit sẽ tạm ngưng để tiết kiệm resource. Khi có visitor mới, app wake up trong 30s. Team dùng hàng ngày → không bao giờ sleep.

**Q: Có thể chỉnh giờ chạy không?**
A: Có. Sửa cron trong `.github/workflows/build_dashboard.yml`. Ví dụ chạy 2 lần/ngày (10h + 20h):
```yaml
- cron: '0 3 * * *'    # 10:00 VN
- cron: '0 13 * * *'   # 20:00 VN
```

**Q: Tại sao KHÔNG dùng Looker Studio?**
A: Xem `docs/PLATFORM_COMPARISON.md`. Ngắn gọn: Streamlit code-first, Looker drag-drop. VietAnh yêu cầu code-first.

**Q: Nếu Refresh Token hết hạn?**
A: Chạy lại `get_refresh_token.py` từ repo `daily-report-affina` cũ để lấy token mới, update GitHub Secret.

**Q: Có thể thêm biểu đồ mới không?**
A: Rất dễ. Mở page tương ứng trong `pages/`, copy 1 chart hiện có, sửa data source + chart type. Push lên main → Streamlit Cloud auto-redeploy trong ~1 phút.

---

## 📞 Support & Contribute

- Gặp lỗi → xem `docs/TROUBLESHOOTING.md` trước
- Muốn thêm chart → sửa file trong `pages/`
- Muốn đổi màu → sửa `COLORS` trong `lib/data.py`

---

## 📜 License

Private / Internal use only — Affina Sales team.
