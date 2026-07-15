# 🎯 PLATFORM COMPARISON — Vì sao chọn Streamlit?

> Đọc file này khi VietAnh (hoặc team) hỏi: **"Tại sao không dùng Looker Studio / Metabase / Power BI?"**

---

## Yêu cầu của VietAnh

Từ tin nhắn ban đầu:

> "Tôi muốn dựng lên dashboard cho 3 file ipynb, trong dashboard chứa các chart đa dạng..."
> "**Dashboard nhất định tôi không muốn đi kéo thả, tôi muốn chạy code để ra luôn dashboard.**"
> "Bạn có thể suggest tôi cái nào tốt nhất."
> "Dashboard đó phải được **auto chạy hàng ngày vào 10h sáng** và là **dashboard real time**"
> "**Có thể share cho bất kì ai** để xem và theo dõi hàng ngày"
> "**Tôi muốn mọi thứ đều miễn phí**"

**7 tiêu chí:**
1. ✅ Code-first (không kéo thả)
2. ✅ Đa dạng chart
3. ✅ Auto chạy 10h sáng
4. ✅ Real-time / near real-time
5. ✅ Share link công khai
6. ✅ Refresh = data mới
7. ✅ Miễn phí

---

## Bảng so sánh chi tiết

| Nền tảng | Code-first | Real-time | Public URL | Auto refresh | Free | Chart lib | Kết luận |
|---|:---:|:---:|:---:|:---:|:---:|---|---|
| **Streamlit Cloud** | ⭐ Python 100% | ✅ (cache TTL) | ✅ | ✅ | ✅ Free forever | Plotly/Altair/Vega | **🏆 CHỌN** |
| Looker Studio | ❌ Drag & drop | ✅ | ✅ | ✅ | ✅ | 20+ built-in | Loại vì drag-drop |
| Metabase Cloud | ⚠️ SQL + UI | ✅ | ✅ | ✅ | ❌ ($85/tháng) | 15+ built-in | Loại vì phí |
| Metabase self-host | ⚠️ SQL + UI | ✅ | ⚠️ Cần server | ✅ | ⚠️ Cần VPS free | 15+ | Cần hosting free (Fly.io) |
| Grafana Cloud | ⚠️ SQL + UI | ✅ | ✅ | ✅ | ✅ Free tier | 40+ | Overkill cho use case này |
| Power BI Service | ❌ | ✅ | ⚠️ Cần AAD login | ✅ | ⚠️ | Nhiều | Không share public |
| Tableau Public | ❌ | ⚠️ Manual publish | ✅ | ❌ | ✅ | Nhiều | Không auto refresh |
| Dash (Plotly) | ⭐ Python | ✅ | ⚠️ Cần host | ✅ | ⚠️ Render/Fly free tier | Plotly | Deploy khó hơn Streamlit |
| Panel/Voila | ⭐ Python | ✅ | ⚠️ | ✅ | ⚠️ | Bokeh/Plotly | Deploy khó |
| Superset | ⚠️ SQL + UI | ✅ | ⚠️ Cần host | ✅ | ⚠️ | 40+ | Enterprise, phức tạp |
| Redash | ⚠️ SQL + UI | ✅ | ⚠️ Self-host | ✅ | ⚠️ | 15+ | Cần hosting |
| Preset (Superset) | ⚠️ | ✅ | ✅ | ✅ | ⚠️ Free 5 user | Nhiều | Giới hạn user |
| Mode Analytics | ⚠️ SQL + Python | ✅ | ✅ | ✅ | ⚠️ Free Studio | Nhiều | Giới hạn 5 report/free |
| Hex | ⚠️ | ✅ | ✅ | ✅ | ⚠️ Free hạn chế | Nhiều | Ít user free |
| Deepnote | ⚠️ Notebook | ✅ | ✅ | ✅ | ⚠️ Free hạn chế | Nhiều | Ít free workspace |

---

## Vì sao **KHÔNG** chọn Looker Studio

Nhìn qua có vẻ Looker Studio là "sinh ra cho bài toán này":
- Miễn phí forever
- Google native → connect Google Sheet 1 phát
- Share link công khai dễ dàng
- Auto refresh khi Google Sheet update
- File 3 gốc đã có bước export Google Sheet **sẵn** cho Looker

**Nhưng VietAnh nói rõ 2 lần trong tin nhắn**: *"KHÔNG kéo thả"* và *"muốn chạy code để ra luôn dashboard"*.

Looker Studio là **UI-first tool**: bạn phải:
1. Vào Looker Studio → tạo Report mới
2. Add Data Source → Google Sheets → chọn Sheet
3. **Drag** field vào chart → chọn chart type
4. **Click** cấu hình color, filter, style
5. Không có "code version" để commit git

Với VietAnh có strong background SQL + Python, tool này **hạn chế khả năng**:
- Custom calculation phức tạp phải viết CALC formula (kém hơn SQL/pandas nhiều)
- Không version control được config chart
- Reuse component gần như không có (phải copy paste chart)
- Debug khó khi chart sai (không có breakpoint)

---

## Vì sao **KHÔNG** chọn Metabase / Grafana

Cả 2 đều là code-friendly hơn Looker, nhưng:

### Metabase
- **Cloud tier**: $85/tháng cho version chính thức → **KHÔNG free**
- **Self-host free**: cần VPS
  - Fly.io free tier có thể chạy 1 Metabase nhỏ nhưng RAM 256MB → không đủ
  - Railway free tier limit
  - Oracle Cloud Free (Ampere 4vCPU) → free forever nhưng setup phức tạp, cần domain, SSL...
- **Chart config vẫn UI-first** — SQL chỉ để define question, còn visualization vẫn phải click
- Learning curve cho team ~1 tuần

### Grafana
- Grafana Cloud free tier tốt nhưng chủ yếu cho **metrics/observability** (Prometheus, Loki), không tối ưu cho business data
- SQL query support ổn nhưng chart type ít business-friendly hơn
- UI trọng tâm là time-series → doanh thu OK, nhưng "top 10 sản phẩm" hoặc "sunburst" thiếu

**Cả 2 đều cần learning + hosting overhead** → không đáng cho use case này.

---

## Vì sao **CHỌN** Streamlit Cloud

### 1. Match 7/7 yêu cầu ✅

| Yêu cầu | Streamlit |
|---|---|
| Code-first | ✅ Pure Python |
| Đa dạng chart | ✅ Plotly (40+ chart types) + Altair + built-in |
| Auto 10h sáng | ✅ GitHub Actions cron (rẻ, ổn định) |
| Real-time | ✅ Cache TTL 5 phút, refresh instant |
| Share link | ✅ `https://<app>.streamlit.app` |
| Refresh mới | ✅ Nút Refresh + auto reload |
| Free | ✅ Community Cloud free forever |

### 2. Đúng "vibe" VietAnh muốn

VietAnh đã có thói quen:
- Viết SQL trong Colab
- pandas transform data
- openpyxl xử lý Excel
- Push Supabase

Streamlit là **extension tự nhiên** của workflow đó:
```python
# Từ notebook → dashboard chỉ cần thêm mấy dòng
import streamlit as st
import plotly.express as px

df = pd.read_sql("SELECT * FROM ...", engine)
st.title("Dashboard")
fig = px.bar(df, x="Channel", y="Doanh thu")
st.plotly_chart(fig)
```

Ai biết pandas là có thể sửa dashboard.

### 3. Version control được

Toàn bộ config chart nằm trong `.py` files → commit git → có history, có review, có branch cho experiment.

### 4. Reuse component

`lib/data.py` có `render_sidebar_filters()` — mọi trang import và dùng. Với Looker phải config filter riêng cho từng report.

### 5. Deployment cực đơn giản

- Push code lên GitHub
- Streamlit Cloud tự pull, build, deploy trong 2-3 phút
- Update code → auto redeploy khi push mới

Không cần config server, không cần Docker, không cần CI/CD phức tạp.

### 6. Community + docs khủng

- Docs tiếng Anh chi tiết: https://docs.streamlit.io
- 30K+ stars GitHub
- Vô số dashboard example trên Streamlit Gallery
- StackOverflow, Discord community rất active

### 7. Không lock-in

Data ở Supabase. Nếu muốn đổi sang tool khác:
- Metabase: connect Supabase, thấy ngay data
- Looker: export bảng ra Google Sheet, connect
- Power BI: connect PostgreSQL

Streamlit chỉ là **presentation layer**, không giam data.

---

## Cân nhắc phụ

### "Streamlit có sleep sau 7 ngày không?"

Có, nhưng:
- Team Affina dùng hàng ngày → **không bao giờ sleep**
- Nếu sleep → click 1 nút wake up → 30 giây → live lại
- Có thể workaround: dùng UptimeRobot ping app mỗi 5 phút (free)

### "Nếu app crash thì sao?"

- Streamlit auto-restart trong 1-2 phút
- Có thể xem log qua Streamlit Cloud dashboard
- Data ở Supabase → không mất

### "Nếu 100 người dùng cùng lúc?"

- 1 GB RAM Streamlit Cloud đủ cho ~50 concurrent users
- Nếu vượt → upgrade Community Cloud Pro ($20/tháng)
- Hoặc deploy trên Fly.io / Render (free tier ~512MB, mount volume)

### "Chart Streamlit đẹp không?"

- Plotly render đẹp hơn Looker khá nhiều
- Theme customize được (`.streamlit/config.toml`)
- Nhiều chart Plotly không có trong Looker: Sunburst, Sankey, Treemap animated, Surface, 3D scatter...

---

## Nếu VietAnh vẫn muốn Looker Studio

Không sao — data đã được prepare sẵn ở bảng `dashboard_master_data`. Chỉ cần:

1. Export bảng ra Google Sheet (viết thêm 1 script `sync_to_gsheet.py`, dùng lại code từ File 3 gốc)
2. Vào Looker Studio → connect Google Sheet
3. Drag drop dashboard

Estimate: ~4 giờ setup. **Nhưng đã có Streamlit rồi, có thể chạy cả 2 song song**.

---

## Kết luận

**Streamlit Cloud** là lựa chọn tối ưu cho 7 yêu cầu của VietAnh. Nếu sau này team lớn (>50 user thường xuyên) hoặc cần feature enterprise (SSO, audit log, custom domain) → move sang Streamlit for Teams ($250/tháng) hoặc self-host Metabase/Superset.

Hiện tại: **$0 chi phí, đáp ứng đủ mọi yêu cầu, deploy trong 30 phút**. Đó là win-win.
