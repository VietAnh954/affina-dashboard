# ☁️ SETUP STREAMLIT CLOUD — Deploy dashboard miễn phí

## Prerequisites

- Đã push code lên GitHub public repo (`VietAnh954/affina-dashboard`)
- Đã setup GitHub Actions & workflow chạy thành công (bảng `dashboard_master_data` có data)

---

## Bước 1 — Đăng ký Streamlit Community Cloud

1. Truy cập https://share.streamlit.io/
2. Click **Sign up** (nếu chưa có account) hoặc **Sign in**
3. Chọn **Continue with GitHub** → authorize
4. Cho phép Streamlit truy cập repo (chỉ cần Public → không cần grant full permission)

---

## Bước 2 — Deploy app

1. Sau khi login, ở dashboard của Streamlit Cloud, click **Create app** (hoặc **New app**)
2. Chọn **Deploy a public app from GitHub**
3. Fill form:

| Field | Value |
|---|---|
| Repository | `VietAnh954/affina-dashboard` |
| Branch | `main` |
| Main file path | `dashboard.py` |
| App URL | `affina-dashboard` *(hoặc tên khác chưa có ai dùng)* |
| Python version | `3.12` |

4. **QUAN TRỌNG**: Click **Advanced settings...**

---

## Bước 3 — Add Secret trên Streamlit Cloud

Trong Advanced Settings, section **Secrets**, paste nội dung:

```toml
SUPABASE_DB_URI = "postgresql://postgres.XXX:PASSWORD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
```

> **Lưu ý:**
> - Chỉ cần 1 secret này (không cần Google credentials vì dashboard chỉ đọc Supabase, không đụng Google Drive)
> - Format TOML: dùng dấu `=`, giá trị trong nháy kép
> - Sau này muốn edit: vào app settings → Secrets

---

## Bước 4 — Deploy

1. Click nút **Deploy!**
2. Streamlit sẽ:
   - Clone repo
   - Cài `requirements.txt`
   - Chạy `streamlit run dashboard.py`
   - Log real-time hiển thị trên UI

3. Chờ ~3-5 phút → thấy dashboard live

4. URL public: `https://affina-dashboard.streamlit.app`

---

## Bước 5 — Verify từng trang

1. Trang chủ 🏠 **Tổng quan** — KPI cards + trend chart hiện được không?
2. Sidebar bên trái → click **📊 Kênh & Sản phẩm** — sunburst render?
3. **👥 Đội ngũ Sales** — sankey diagram + scatter?
4. **📅 Phân tích thời gian** — YoY bar + heatmap?
5. **🔍 Chi tiết & Filter** — table + download button?

Nếu 1 trong 5 trang fail:
- Vào Streamlit app → "Manage app" (góc dưới phải) → click "Logs"
- Xem stack trace, copy sang ChatGPT/Claude phân tích

---

## Bước 6 — Test share cho người khác

1. Copy URL: `https://affina-dashboard.streamlit.app`
2. Mở incognito/private tab (KHÔNG login GitHub) → paste URL
3. Verify: dashboard load, không bắt login → OK ✅

---

## 🎨 Tùy chỉnh nâng cao

### Đổi favicon + tên app

Sửa dòng đầu của `dashboard.py`:
```python
st.set_page_config(
    page_title="Affina Sales Dashboard",  # ← đây
    page_icon="🏢",                        # ← emoji hoặc URL ảnh
    layout="wide",
)
```

### Đổi màu theme

Sửa `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1F4E78"        # màu accent (button, active state)
backgroundColor = "#FFFFFF"      # nền chính
secondaryBackgroundColor = "#F5F7FA"  # nền sidebar
textColor = "#2C3E50"
```

Push commit → Streamlit auto-redeploy trong ~1 phút.

### Custom domain (Optional, paid)

Streamlit Community Cloud không hỗ trợ custom domain cho free tier.
Nếu muốn `dashboard.affina.vn`:
- **Option 1**: Streamlit Teams ($20/month/user)
- **Option 2**: Deploy Streamlit lên Fly.io/Railway (free tier) + cấu hình CNAME
- **Option 3**: Cloudflare Worker proxy → miễn phí, cần setup

---

## 🔄 Cách app tự update khi push code

Không cần setup gì thêm. Streamlit Cloud tự động:
1. Watch main branch của repo
2. Khi có commit mới → tự pull code
3. Restart app với code mới
4. Users next visit thấy update

Thời gian từ push đến live: ~30-60 giây.

**Test:**
```powershell
# Sửa 1 dòng nhỏ, VD title dashboard
# Sửa dashboard.py: st.title("🏠 Tổng quan v2")

git add dashboard.py
git commit -m "test: change title"
git push origin main

# Chờ ~60s, refresh browser, xem title đã đổi
```

---

## 🐌 App bị sleep — behavior thường gặp

**Vấn đề**: Sau 7 ngày không ai truy cập, app tự tạm ngưng.

**Trải nghiệm user**:
- User mở link → hiện màn hình "This app has gone to sleep..."
- Có nút "Get this app back up!" → click → chờ ~30s
- App wake up → user thấy dashboard

**Cách tránh sleep**:
- Setup UptimeRobot (free) ping URL mỗi 5 phút → app không bao giờ sleep
- Hoặc: team dùng hàng ngày → không có cửa sổ 7 ngày inactive

**UptimeRobot setup (Optional):**
1. https://uptimerobot.com/ → Sign up free
2. New Monitor → Monitor Type: HTTP(s)
3. URL: `https://affina-dashboard.streamlit.app`
4. Monitoring Interval: 5 minutes
5. Save

---

## 📊 Quota Streamlit Community Cloud

| Resource | Limit |
|---|---|
| Apps per workspace | Unlimited (public) |
| RAM per app | 1 GB |
| CPU | 1 core (shared) |
| Storage | Ephemeral (mất khi restart) |
| Data upload | 200 MB per file (config-able) |
| Compute time | Unlimited |
| Sleep policy | Sau 7 ngày inactive |

Với dashboard này (đọc từ Supabase, không lưu local):
- Data ~50k rows × 60 cols → memory dùng ~50-100 MB
- Nhiều user cùng lúc → mỗi user 1 session độc lập
- Bottleneck sẽ là Supabase (không phải Streamlit)

---

## 🚨 Troubleshooting

### App fail deploy — "ModuleNotFoundError"

→ Thiếu package trong `requirements.txt`. Add package → push → auto-redeploy.

### App load nhưng chart trống

→ Bảng `dashboard_master_data` trống. Chạy GitHub Actions workflow "Build Dashboard Data" thủ công.

### App load rất chậm (>10s)

→ Cache đang miss. Bấm refresh 1 lần nữa, lần sau sẽ nhanh (cached 5 phút).
→ Nếu vẫn chậm: bảng có thể đã lớn (>1M rows). Cân nhắc:
- Giới hạn thời gian trong build script (chỉ 2 năm gần nhất)
- Aggregate data trước khi push (thay vì detail level)

### Secret bị leak lên GitHub

Nếu accidentally commit `.env` hoặc `secrets.toml`:
1. **Revoke ngay** secret bị leak (Supabase → reset password, Google → revoke OAuth)
2. Rewrite git history:
   ```powershell
   pip install git-filter-repo
   git filter-repo --path .env --invert-paths
   git push origin --force main
   ```
3. Tạo credentials mới → update GitHub Secrets + Streamlit Secrets

---

## ✅ Hoàn tất!

Dashboard đã live tại: **`https://affina-dashboard.streamlit.app`**

Share link cho team. Tự động refresh mỗi ngày 10h sáng. Zero cost. Zero maintenance.

Nếu muốn thêm chart mới → sửa file trong `pages/`, push, chờ 1 phút.
