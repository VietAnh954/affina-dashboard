# 🔧 SETUP GITHUB ACTIONS — Hướng dẫn chi tiết

## Mục tiêu

Cấu hình GitHub Actions để tự động chạy `scripts/build_dashboard_data.py` hàng ngày 10:00 VN, sync data lên Supabase cho Streamlit dashboard đọc.

---

## Bước 1 — Tạo repo GitHub

1. Truy cập https://github.com/new
2. Fill form:
   - **Owner**: `VietAnh954`
   - **Repository name**: `affina-dashboard`
   - **Visibility**: ✅ **Public**
     > Public để dùng Streamlit Community Cloud FREE. Nếu Private, phải trả phí Streamlit.
   - Uncheck "Add a README file" (có sẵn trong package)
   - Uncheck "Add .gitignore"
   - Uncheck "Choose a license"
3. Click **Create repository**

---

## Bước 2 — Push code local lên GitHub

```powershell
cd C:\Users\ADMIN\Desktop\AFFINA\CODE\build_test

# Init git
git init
git add .

# Verify không có secrets trong commit
git status | findstr /I secrets
git status | findstr /I ".env"
# Cả 2 lệnh trên phải TRỐNG (không match gì)

# Commit + push
git commit -m "feat: initial affina dashboard"
git branch -M main
git remote add origin https://github.com/VietAnh954/affina-dashboard.git
git push -u origin main
```

Nếu push lần đầu bị bắt login → dùng GitHub Personal Access Token (Settings → Developer settings → PAT).

---

## Bước 3 — Setup 4 GitHub Secrets

Vào https://github.com/VietAnh954/affina-dashboard/settings/secrets/actions

Click **New repository secret** và add lần lượt 4 secret:

### Secret 1: `SUPABASE_DB_URI`

- Name: `SUPABASE_DB_URI`
- Value: connection string PostgreSQL của Supabase
  - Format: `postgresql://postgres.XXX:PASSWORD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres`
  - Copy từ Supabase Dashboard → Settings → Database → Connection String (Session mode)

### Secret 2: `GOOGLE_CLIENT_ID`

- Name: `GOOGLE_CLIENT_ID`
- Value: OAuth Client ID (dạng `xxxxx.apps.googleusercontent.com`)
- Copy từ Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs

### Secret 3: `GOOGLE_CLIENT_SECRET`

- Name: `GOOGLE_CLIENT_SECRET`
- Value: OAuth Client Secret (dạng `GOCSPX-xxxxx`)
- Copy từ cùng nơi với Client ID

### Secret 4: `GOOGLE_REFRESH_TOKEN`

- Name: `GOOGLE_REFRESH_TOKEN`
- Value: Refresh Token đã lấy bằng `get_refresh_token.py`
- Nếu chưa có, chạy lại script này từ repo `daily-report-affina` cũ

**Tất cả 4 giá trị này giống hệt bên repo `daily-report-affina`** — có thể copy trực tiếp.

---

## Bước 4 — Test workflow thủ công

1. Vào https://github.com/VietAnh954/affina-dashboard/actions
2. Sidebar trái → click **"Build Dashboard Data"**
3. Nút **Run workflow** (phía phải) → chọn Branch `main` → Click **Run workflow**
4. Đợi ~10 giây → refresh trang → thấy row mới "In progress" 🟡
5. Click vào row → xem log real-time
6. Sau ~3-5 phút, status chuyển thành **Success** ✅

### Log cần verify

Trong tab "build" của run, phần "Run build_dashboard_data.py", log cuối phải có:

```
[2026-07-15 10:03:12] BUILD DASHBOARD DATA — DONE in 156.34s
  Rows: 45,231
  Core=12,345 | Neo=8,765 | TSA=24,121
```

Nếu thấy `[FATAL]`, log lỗi ở dòng gần đó — copy sang ChatGPT/Claude để phân tích, hoặc xem `TROUBLESHOOTING.md`.

---

## Bước 5 — Verify cron sẽ chạy tự động

1. Ở Actions page, click "Build Dashboard Data"
2. Nhìn text nhỏ dưới tên workflow: "This workflow has a `schedule` event trigger"
3. Xem **Next scheduled run**: sẽ là 10:00 VN ngày hôm sau (03:00 UTC)

> ⏰ **Lưu ý về GitHub Actions cron:**
> - Cron trên GitHub có thể chậm 5-30 phút so với thời gian yêu cầu, do hàng đợi free tier
> - Đây là hành vi bình thường, không phải bug
> - Nếu cần chạy đúng giờ tuyệt đối, chuyển sang chạy trên server riêng (paid)

---

## Bước 6 — Cấu hình notification (Optional)

Nếu muốn nhận email khi workflow fail:

1. Vào GitHub → click avatar → **Settings**
2. **Notifications** (sidebar trái)
3. **System** → **Actions** → check **Send notifications for failed workflows only**

---

## 🔄 Cách chỉnh sửa lịch chạy

Muốn đổi giờ chạy? Sửa file `.github/workflows/build_dashboard.yml`, dòng `cron`:

**Công thức**: Giờ VN - 7 = Giờ UTC

| Giờ chạy mong muốn (VN) | Cron (UTC) |
|---|---|
| 06:00 sáng | `0 23 * * *` (23:00 UTC hôm trước) |
| 08:00 sáng | `0 1 * * *` |
| **10:00 sáng (default)** | **`0 3 * * *`** |
| 12:00 trưa | `0 5 * * *` |
| 17:00 chiều | `0 10 * * *` |
| 20:00 tối | `0 13 * * *` |

**Chạy 2 lần/ngày** (VD 10h + 20h):
```yaml
schedule:
  - cron: '0 3 * * *'    # 10:00 VN
  - cron: '0 13 * * *'   # 20:00 VN
```

**Chỉ chạy ngày làm việc (thứ 2-6)**:
```yaml
schedule:
  - cron: '0 3 * * 1-5'
```

Sau khi sửa, commit + push:
```powershell
git add .github/workflows/build_dashboard.yml
git commit -m "chore: đổi lịch chạy sang 20:00 VN"
git push origin main
```

---

## 🚨 Các lỗi phổ biến

| Lỗi | Fix |
|---|---|
| `Error: Process completed with exit code 1` (không có log rõ) | Vào tab Job → expand từng step → tìm bước nào fail. Copy log lỗi. |
| `FATAL: Thiếu env: ['SUPABASE_DB_URI']` | Chưa add secret hoặc tên secret sai. Vào Settings → Secrets → verify tên và value. |
| `HttpError 403: refresh token expired` | User đã revoke Google access. Chạy lại `get_refresh_token.py` → update secret `GOOGLE_REFRESH_TOKEN`. |
| `psycopg2.OperationalError: SSL connection has been closed unexpectedly` | Supabase free đôi khi drop connection. `pool_pre_ping=True` trong code đã handle. Retry lần 2. |
| Workflow không tự chạy đúng giờ | GitHub Actions cron trễ 5-30 phút là bình thường. Không phải bug. |
| `google.auth.exceptions.RefreshError: ('invalid_grant: Bad Request', ...)` | Refresh Token bị revoke hoặc sai format. Lấy token mới. |

---

## 📊 Monitoring

- **GitHub Actions dashboard**: https://github.com/VietAnh954/affina-dashboard/actions
- **Log run cụ thể**: click vào từng run
- **Historical**: xem 30 run gần nhất, biết pattern fail

Recommend: check Actions mỗi tuần 1 lần để đảm bảo không có run nào fail liên tục.
