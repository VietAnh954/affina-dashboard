# 📊 DASHBOARD DESIGN — Thiết kế chi tiết từng trang & chart

> **Nguyên tắc thiết kế**: mỗi chart phải trả lời 1 câu hỏi kinh doanh cụ thể, không "chart for the sake of chart".

---

## Sidebar (áp dụng cho mọi trang)

```
┌──────────────────────────┐
│  🎯 Bộ lọc chung          │
│                          │
│  📅 Khoảng thời gian     │
│  [01/01/2024]            │
│  [31/12/2026]            │
│                          │
│  🎨 Source               │
│  ☑ Core                  │
│  ☑ Neo                   │
│  ☑ TSA                   │
│                          │
│  📡 Channel               │
│  [dropdown multi]        │
│                          │
│  🛡 Loại BH              │
│  [dropdown multi]        │
│                          │
│  🏢 Nhà BH               │
│  [dropdown multi]        │
│                          │
│  ─────────────────       │
│  🔄 Refresh Data         │
│  ─────────────────       │
│  🕒 Last updated:        │
│  15/07/2026 10:03 UTC+7  │
│  Rows: 45,231            │
└──────────────────────────┘
```

---

## Trang 1 — 🏠 Tổng quan (`dashboard.py`)

**Mục tiêu:** Ban lãnh đạo mở lên là thấy ngay bức tranh toàn cảnh.

### Section 1.1 — 7 KPI Cards (hàng ngang)

| KPI | Formula | Format |
|---|---|---|
| Tổng doanh thu | `SUM(Doanh thu trước thuế)` | 12.3B VNĐ |
| Tổng phí BH | `SUM(Phí BH (VNĐ))` | 15.8B VNĐ |
| Số HĐ | `COUNT(DISTINCT Số hợp đồng)` | 8,742 |
| Affina Revenue | `SUM(Affina_Revenue)` | 1.4B VNĐ |
| EST Bonus | `SUM(EST_Bonus)` | 2.1B VNĐ |
| Số Sale active | `COUNT(DISTINCT Họ tên sale)` | 342 |
| AVG revenue/HĐ | `SUM(Doanh thu)/COUNT(HĐ)` | 1.8M VNĐ |

Mỗi card có: giá trị chính + % thay đổi so với period trước (dùng `st.metric`)

### Section 1.2 — 2 chart chính (2 cột)

**Chart 1.2.A — Line: Doanh thu theo tháng, split Source**
- X: Tháng-Năm (YYYY-MM)
- Y: Doanh thu trước thuế
- Series: Core (xanh dương), Neo (cam), TSA (xanh lá)
- Type: Plotly line chart + area fill dưới line, opacity 0.2
- Interactive: hover show exact value

**Chart 1.2.B — Donut: Cơ cấu doanh thu theo Source**
- Values: SUM doanh thu
- Labels: Core / Neo / TSA
- Center text: Total revenue
- Colors match line chart

### Section 1.3 — Sparkline row (3 cột)

3 mini sparklines cho 3 metric key theo 30 ngày gần nhất:
- Số HĐ mỗi ngày
- Doanh thu mỗi ngày
- Affina Revenue mỗi ngày

Dùng `st.line_chart` (nhẹ, đẹp).

### Section 1.4 — Bảng Top 10 (2 cột)

- **Bảng 1.4.A**: Top 10 Sale by Doanh thu (rank, tên, doanh thu, EST_Bonus)
- **Bảng 1.4.B**: Top 10 Nhà BH by Doanh thu

---

## Trang 2 — 📊 Kênh & Sản phẩm (`pages/2_📊_Kenh_va_San_pham.py`)

**Mục tiêu:** Hiểu mix sản phẩm, kênh nào bán tốt, sản phẩm nào là ngôi sao.

### Section 2.1 — Sunburst: Source → Channel → Loại BH → Sản phẩm

Chart Plotly Sunburst thể hiện phân cấp:
- Vòng trong: Source (Core/Neo/TSA)
- Vòng giữa: Channel
- Vòng ngoài: Loại BH
- Vòng ngoài cùng: Top 10 sản phẩm mỗi Loại BH

Click vào 1 phần → zoom vào phần đó. Rất mạnh cho drill-down.

### Section 2.2 — Bar chart: Doanh thu theo Channel (horizontal)

- Y-axis: Channel name
- X-axis: Doanh thu trước thuế
- Sort giảm dần
- Color: theo Source
- Show data labels

### Section 2.3 — Treemap: Nhà BH × Loại BH

- Rectangle size ∝ Doanh thu
- Group by: Nhà BH → Loại BH
- Show label + value
- Color scale theo Affina_Revenue

### Section 2.4 — Grouped Bar: Top 15 sản phẩm × Kênh

- X: Sản phẩm
- Y: Doanh thu
- Groups: Core/Neo/TSA (3 bar mỗi sản phẩm)
- Rotate x-label 45°

### Section 2.5 — Pie: Loại bảo hiểm (BHSK/BHXM/BHYT/…)

- 7 slices tương ứng 7 loại BH
- Show % + value tooltip

### Section 2.6 — Stacked bar: Add-ons BHSK

Đối với riêng BHSK, breakdown thêm:
- Có Ngoại trú (Có/Không)
- Có Nha khoa
- Có Thai sản
- Có Topup

→ 4 stacked bar chart nhỏ để so sánh tỉ lệ.

---

## Trang 3 — 👥 Đội ngũ Sales (`pages/3_👥_Doi_ngu_Sales.py`)

**Mục tiêu:** Ranking sale, hierarchy manager, phát hiện star performer & underperformer.

### Section 3.1 — Top 20 Salesperson

Horizontal bar chart:
- Y: Họ tên sale (sort by revenue)
- X: Doanh thu trước thuế
- Color: theo Chức danh
- Có filter dropdown chọn "chỉ Core / chỉ Neo / chỉ TSA / All"

### Section 3.2 — BDM Performance (Manager level 1)

Card grid — mỗi BDM 1 card:
- Tên BDM
- Số sale dưới quyền
- Tổng doanh thu team
- % đạt target (nếu có target — placeholder now)
- Mini sparkline

### Section 3.3 — BDD Performance (Manager level 2)

Tương tự BDM.

### Section 3.4 — Sankey diagram: Sale → BDM → BDD

Luồng: mỗi CTV → BDM quản lý → BDD quản lý. Width flow ∝ doanh thu.

→ Rất trực quan để thấy manager nào có team hiệu quả.

### Section 3.5 — Scatter: Số HĐ vs Doanh thu (mỗi điểm = 1 sale)

- X: Số HĐ
- Y: Doanh thu trước thuế
- Size: Affina_Revenue
- Color: Chức danh
- Hover: tên sale, BDM, BDD

→ Phát hiện:
- Góc trên-phải: star (nhiều HĐ + doanh thu cao)
- Góc trên-trái: bán giá cao ít HĐ
- Góc dưới-phải: bán rẻ nhiều HĐ

### Section 3.6 — Bảng chi tiết all sales (với sort, search)

Cột: Tên | Chức danh | BDM | BDD | Số HĐ | Doanh thu | EST_Bonus | Affina Revenue
+ Nút download CSV

---

## Trang 4 — 📅 Phân tích theo thời gian (`pages/4_📅_Phan_tich_thoi_gian.py`)

**Mục tiêu:** Xu hướng, mùa vụ, so sánh cùng kỳ, forecast đơn giản.

### Section 4.1 — YoY Comparison (Bar chart)

- X: 12 tháng (Jan-Dec)
- Y: Doanh thu
- 3 series: 2024 (xám), 2025 (xanh nhạt), 2026 (xanh đậm)
- Show % YoY growth trên mỗi bar 2026

### Section 4.2 — MoM Growth Rate (Line + bar combo)

- X: Tháng
- Bar: Doanh thu tháng đó
- Line trên bar: % MoM change
- 2 trục Y

### Section 4.3 — Heatmap: Ngày trong tuần × Tuần trong năm

- Row: Thứ 2 → Chủ nhật
- Col: Tuần 1 → Tuần 52
- Cell color: Doanh thu
- Có toggle: theo Số HĐ / Doanh thu / EST_Bonus

→ Phát hiện pattern: bán tốt vào thứ mấy, tuần nào peak

### Section 4.4 — Cumulative revenue (Area chart)

- X: Ngày
- Y: Cumulative doanh thu
- 3 series: Core, Neo, TSA
- Có annotation cho các event: bùng nổ B-One 07-08/2025, chương trình BHXM 08-09/2025

### Section 4.5 — 30-day forecast (Line chart)

- Data: 90 ngày qua
- Model: đơn giản `prophet` hoặc rolling avg → forecast 30 ngày tới
- Show confidence interval

*(Có thể phase 2 nếu phức tạp — giai đoạn đầu chỉ show historical trend)*

### Section 4.6 — Life-time contract expiry

- Histogram: distribution của (Ngày kết thúc - hôm nay) trong tháng
- Phát hiện HĐ nào sắp hết → có action tái tục

---

## Trang 5 — 🔍 Chi tiết & Filter (`pages/5_🔍_Chi_tiet_va_Filter.py`)

**Mục tiêu:** Cho phép user query/filter/export raw data — thay thế cho việc phải mở file Excel.

### Section 5.1 — Multi-filter panel

Ngoài sidebar chung, thêm filter chi tiết:
- Text search: Tên NĐBH, Tên NMBH, Số hợp đồng
- Range slider: Số tiền thanh toán từ ... đến ...
- Multiselect: Sale, BDM, BDD, Nhà BH

### Section 5.2 — Interactive DataTable

- Dùng `st.dataframe` với `column_config`
- Cột số hiển thị format VNĐ
- Cột ngày hiển thị dd/mm/yyyy
- Có sort/search built-in
- Pagination

### Section 5.3 — Download button

- Download filtered data as CSV (nút "📥 Tải xuống CSV")
- Download filtered data as Excel với format (nút "📥 Tải xuống Excel")

### Section 5.4 — Statistical summary

- Sau khi filter, show:
  - Số dòng: 1,234
  - Tổng doanh thu: xxx VNĐ
  - AVG doanh thu/HĐ: xxx VNĐ
  - Ngày cũ nhất → mới nhất

---

## 🎨 Design system

### Color palette

```python
COLORS = {
    "Core": "#1F77B4",   # Xanh dương (trust)
    "Neo":  "#FF7F0E",   # Cam (energy)
    "TSA":  "#2CA02C",   # Xanh lá (fresh)
    "positive": "#2CA02C",
    "negative": "#D62728",
    "warning": "#F1C40F",
    "background": "#FAFAFA",
    "text": "#2C3E50",
    # 7 loại BH
    "BHSK": "#E74C3C",
    "BHXM": "#3498DB",
    "BHYT/BHXH": "#9B59B6",
    "BHOTO": "#F39C12",
    "BHDL": "#1ABC9C",
    "TNDS": "#34495E",
    "BHRR": "#E67E22",
}
```

### Typography

- Font: default Streamlit (System UI)
- Number format: `f"{x:,.0f} ₫"` for VNĐ, `f"{x:.1%}"` for percentage
- Date format: `dd/mm/yyyy`

### Layout

- Wide layout: `st.set_page_config(layout="wide")`
- 2-3 column layouts using `st.columns([1,1,1])`
- Section separator: `st.divider()`
- Big titles: `st.title()`, section titles: `st.header()`, subsection: `st.subheader()`

### Chart config chung

```python
import plotly.express as px

def _apply_layout(fig, title=""):
    fig.update_layout(
        title=title,
        template="plotly_white",
        font=dict(family="Segoe UI, Arial", size=12),
        margin=dict(l=30, r=20, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(font_size=13),
    )
    return fig
```

---

## Tương tác & UX

1. **Nút "🔄 Refresh Data"** ở sidebar → clear cache → fetch lại từ Supabase
2. **Loading spinner** khi query DB (built-in Streamlit)
3. **Empty state**: nếu filter ra 0 row → show message "Không có dữ liệu phù hợp bộ lọc"
4. **Error state**: nếu Supabase timeout → show retry button
5. **Mobile responsive**: Streamlit tự lo, các column tự stack khi màn hình nhỏ

---

## Chỉ số thành công (KPI dashboard)

Dashboard được coi là thành công nếu:
1. ✅ Load < 3 giây (kể cả người đầu tiên gọi trong 5 phút)
2. ✅ Team truy cập được từ điện thoại
3. ✅ Filter cho ra kết quả đúng, đầy đủ
4. ✅ Không cần training — nhìn là hiểu
5. ✅ Data mới nhất luôn <24h (auto build 10h sáng mỗi ngày)

---

Đọc tiếp `TASKLIST.md` để có checklist chi tiết implement.
