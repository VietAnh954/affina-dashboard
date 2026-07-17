"""
================================================================================
 AFFINA DASHBOARD — Trang chủ (Tổng quan)
================================================================================
Streamlit app đọc dữ liệu từ Supabase (bảng dashboard_master_data + dashboard_meta)
và hiển thị dashboard real-time cho team Affina.

Chạy local:
    streamlit run dashboard.py

Deploy: Streamlit Community Cloud (share.streamlit.io)
Secrets cần: SUPABASE_DB_URI
================================================================================
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from lib.data import (
    COLORS, DATE_COL,
    apply_filters, apply_plotly_layout, empty_state,
    fmt_num, fmt_vnd,
    load_master_data, render_sidebar_filters,
)
from lib.i18n import t

# ============================================================================
# Page config — chỉ chạy 1 lần cho trang chủ
# ============================================================================
st.set_page_config(
    page_title="Affina Sales Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Affina Sales Dashboard — Auto-updated daily at 10:00 VN",
    },
)

from lib.auth import require_auth
require_auth("home", "Tong quan")

from lib.theme import inject_css
inject_css()


# CSS injected via lib/theme.py inject_css() above

# ============================================================================
# Header với logo
# ============================================================================
st.markdown(
    """<div style="display:flex; align-items:center; gap:16px; margin-bottom:8px;">
        <div style="font-size:36px; font-weight:800; letter-spacing:4px;
                    background: linear-gradient(135deg, #E85BD8, #8B6FC9);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            AFFINA
        </div>
        <div>
            <div style="font-size:22px; font-weight:700; color:#3D2B4F;">Sales Dashboard</div>
            <div style="font-size:13px; color:#7D5BA6; margin-top:2px;">
                Tram viec da kho, Bao hiem co Affina lo
            </div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

# ============================================================================
# Load & filter
# ============================================================================
df_raw = load_master_data()
if df_raw.empty:
    st.warning("Chưa có dữ liệu trong bảng `dashboard_master_data`.")
    st.info(
        "**Cách khắc phục:**\n\n"
        "1. Vào GitHub repo Actions tab\n"
        "2. Chọn workflow **Build Dashboard Data**\n"
        "3. Click **Run workflow** Run workflow\n"
        "4. Chờ ~3-5 phút, sau đó reload trang này"
    )
    st.stop()

filters = render_sidebar_filters(df_raw)
df = apply_filters(df_raw, filters)

if df.empty:
    empty_state("Không có dữ liệu phù hợp bộ lọc. Vui lòng điều chỉnh filter ở sidebar.")
    st.stop()

# ============================================================================
# SECTION 1 — KPI Cards
# ============================================================================
st.markdown("### Chỉ số kinh doanh chính")

def _sum(col: str) -> float:
    return float(df[col].sum()) if col in df.columns else 0.0

total_rev = _sum("Doanh thu trước thuế")
total_pay = _sum("Số tiền thanh toán")
total_prem = _sum("Phí BH (VNĐ)")
total_affina = _sum("Affina_Revenue")
total_bonus = _sum("EST_Bonus")
total_hd = df["Số hợp đồng"].nunique() if "Số hợp đồng" in df.columns else 0
n_sales = df["Họ tên sale"].nunique() if "Họ tên sale" in df.columns else 0
avg_per_hd = total_rev / total_hd if total_hd else 0

# So sánh với period trước cùng độ dài (để hiện delta)
delta_rev = delta_hd = None
if DATE_COL in df.columns and df[DATE_COL].notna().any():
    period_len = (filters["end_date"] - filters["start_date"]).days + 1
    prev_start = filters["start_date"] - pd.Timedelta(days=period_len)
    prev_end = filters["start_date"] - pd.Timedelta(days=1)
    df_prev = df_raw[
        (df_raw[DATE_COL] >= prev_start) &
        (df_raw[DATE_COL] <= prev_end + pd.Timedelta(days=1))
    ]
    # Apply cùng filter Source/Channel/Loại BH/Nhà BH lên period trước
    if filters["sources"]: df_prev = df_prev[df_prev["Source"].isin(filters["sources"])]
    if filters["channels"]: df_prev = df_prev[df_prev["Channel"].isin(filters["channels"])]
    if filters["loai_bh"]: df_prev = df_prev[df_prev["Loại bảo hiểm"].isin(filters["loai_bh"])]
    if filters["nha_bh"]: df_prev = df_prev[df_prev["Nhà BH"].isin(filters["nha_bh"])]

    if not df_prev.empty:
        prev_rev = float(df_prev["Doanh thu trước thuế"].sum()) if "Doanh thu trước thuế" in df_prev else 0
        prev_hd = df_prev["Số hợp đồng"].nunique() if "Số hợp đồng" in df_prev else 0
        if prev_rev > 0:
            delta_rev = f"{((total_rev - prev_rev) / prev_rev) * 100:+.1f}% so kỳ trước"
        if prev_hd > 0:
            delta_hd = f"{((total_hd - prev_hd) / prev_hd) * 100:+.1f}% so kỳ trước"

# Hàng 1: 4 KPI chính
c1, c2, c3, c4 = st.columns(4)
c1.metric("Doanh thu trước thuế", fmt_vnd(total_rev, short=True), delta=delta_rev)
c2.metric("Tổng thanh toán", fmt_vnd(total_pay, short=True))
c3.metric("Số hợp đồng", fmt_num(total_hd), delta=delta_hd)
c4.metric("Affina Revenue", fmt_vnd(total_affina, short=True))

# Hàng 2: 4 KPI phụ
c5, c6, c7, c8 = st.columns(4)
c5.metric("EST Bonus", fmt_vnd(total_bonus, short=True))
c6.metric("Phí BH (Premium)", fmt_vnd(total_prem, short=True))
c7.metric("Sale active", fmt_num(n_sales))
c8.metric("AVG DT / HĐ", fmt_vnd(avg_per_hd, short=True))

st.divider()

# ============================================================================
# SECTION 2 — Xu hướng & Cơ cấu (2 cột)
# ============================================================================
st.markdown("### Xu hướng & Cơ cấu")
col_left, col_right = st.columns([3, 2])

with col_left:
    # Line chart: doanh thu theo tháng, split by Source (area)
    if DATE_COL in df.columns and df[DATE_COL].notna().any():
        df_m = df.copy()
        df_m["month"] = df_m[DATE_COL].dt.to_period("M").dt.to_timestamp()
        grp = (df_m.groupby(["month", "Source"], as_index=False)["Doanh thu trước thuế"]
                    .sum()
                    .rename(columns={"Doanh thu trước thuế": "revenue"}))
        if not grp.empty:
            fig = px.line(
                grp, x="month", y="revenue", color="Source",
                color_discrete_map=COLORS,
                markers=True,
                labels={"month": "Tháng", "revenue": "Doanh thu (VNĐ)"},
            )
            fig.update_traces(line=dict(width=2.5))
            fig.update_layout(hovermode="x unified")
            fig.update_yaxes(tickformat=",.0f")
            fig.update_xaxes(dtick="M1", tickformat="%m/%Y")
            st.plotly_chart(
                apply_plotly_layout(fig, title="Doanh thu theo tháng (chia theo Source)", height=420),
                use_container_width=True,
            )
        else:
            empty_state("Không đủ dữ liệu vẽ trend.")
    else:
        st.info("Không có cột 'Ngày thanh toán' để vẽ trend.")

with col_right:
    # Donut: cơ cấu doanh thu theo Source
    src_rev = df.groupby("Source", as_index=False)["Doanh thu trước thuế"].sum()
    src_rev = src_rev[src_rev["Doanh thu trước thuế"] > 0]
    if not src_rev.empty:
        fig = px.pie(
            src_rev, names="Source", values="Doanh thu trước thuế",
            hole=0.55, color="Source", color_discrete_map=COLORS,
        )
        fig.update_traces(
            textposition="outside",
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Doanh thu: %{value:,.0f} ₫<extra></extra>",
        )
        fig.add_annotation(
            text=(f"<b>{fmt_vnd(src_rev['Doanh thu trước thuế'].sum(), short=True)}</b>"
                  f"<br><span style='font-size:11px'>Tổng DT</span>"),
            x=0.5, y=0.5, showarrow=False, font=dict(size=16),
        )
        st.plotly_chart(
            apply_plotly_layout(fig, title="Cơ cấu doanh thu theo Source", height=420),
            use_container_width=True,
        )
    else:
        empty_state()

st.divider()

# ============================================================================
# SECTION 3 — Sparkline 30 ngày gần nhất
# ============================================================================
st.markdown("### 30 ngày gần nhất (trong khoảng lọc)")
if DATE_COL in df.columns and df[DATE_COL].notna().any():
    last_date = df[DATE_COL].max()
    d30 = df[df[DATE_COL] >= (last_date - pd.Timedelta(days=30))]
    if not d30.empty:
        daily = (d30.groupby(d30[DATE_COL].dt.date)
                     .agg(revenue=("Doanh thu trước thuế", "sum"),
                          n_hd=("Số hợp đồng", "nunique"),
                          affina=("Affina_Revenue", "sum"))
                     .reset_index()
                     .rename(columns={DATE_COL: "date"}))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Doanh thu / ngày")
            st.line_chart(daily.set_index("date")["revenue"], height=160)
            st.metric("Tổng 30 ngày", fmt_vnd(daily["revenue"].sum(), short=True),
                      delta=f"TB {fmt_vnd(daily['revenue'].mean(), short=True)}/ngày")
        with c2:
            st.caption("Số HĐ / ngày")
            st.line_chart(daily.set_index("date")["n_hd"], height=160)
            st.metric("Tổng 30 ngày", fmt_num(daily["n_hd"].sum()),
                      delta=f"TB {daily['n_hd'].mean():.0f} HĐ/ngày")
        with c3:
            st.caption("Affina Revenue / ngày")
            st.line_chart(daily.set_index("date")["affina"], height=160)
            st.metric("Tổng 30 ngày", fmt_vnd(daily["affina"].sum(), short=True),
                      delta=f"TB {fmt_vnd(daily['affina'].mean(), short=True)}/ngày")
    else:
        empty_state("Không có giao dịch trong 30 ngày gần nhất của khoảng lọc.")

st.divider()

# ============================================================================
# SECTION 4 — Top 10 (2 bảng)
# ============================================================================
st.markdown(f"### {t('home_top10_title')}")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Top 10 Sale theo Doanh thu**")
    if "Họ tên sale" in df.columns:
        top_sale = (df.groupby("Họ tên sale", as_index=False)
                      .agg(revenue=("Doanh thu trước thuế", "sum"),
                           n_hd=("Số hợp đồng", "nunique"),
                           bonus=("EST_Bonus", "sum"))
                      .sort_values("revenue", ascending=False)
                      .head(10))
        if not top_sale.empty:
            top_sale.insert(0, "#", range(1, len(top_sale) + 1))
            top_sale["Doanh thu"] = top_sale["revenue"].apply(lambda v: fmt_vnd(v, short=True))
            top_sale["EST_Bonus"] = top_sale["bonus"].apply(lambda v: fmt_vnd(v, short=True))
            top_sale["Số HĐ"] = top_sale["n_hd"].apply(fmt_num)
            st.dataframe(
                top_sale[["#", "Họ tên sale", "Số HĐ", "Doanh thu", "EST_Bonus"]],
                hide_index=True, use_container_width=True,
            )
        else:
            empty_state()
    else:
        st.info("Không có cột 'Họ tên sale'")

with col2:
    st.markdown("**Top 10 Nhà bảo hiểm theo Doanh thu**")
    if "Nhà BH" in df.columns:
        top_p = (df.groupby("Nhà BH", as_index=False)
                   .agg(revenue=("Doanh thu trước thuế", "sum"),
                        n_hd=("Số hợp đồng", "nunique"),
                        affina=("Affina_Revenue", "sum"))
                   .sort_values("revenue", ascending=False)
                   .head(10))
        if not top_p.empty:
            top_p.insert(0, "#", range(1, len(top_p) + 1))
            top_p["Doanh thu"] = top_p["revenue"].apply(lambda v: fmt_vnd(v, short=True))
            top_p["Affina Rev"] = top_p["affina"].apply(lambda v: fmt_vnd(v, short=True))
            top_p["Số HĐ"] = top_p["n_hd"].apply(fmt_num)
            st.dataframe(
                top_p[["#", "Nhà BH", "Số HĐ", "Doanh thu", "Affina Rev"]],
                hide_index=True, use_container_width=True,
            )
        else:
            empty_state()

st.divider()

# ============================================================================
# SECTION 5 — Navigation hint
# ============================================================================
st.markdown("### Khám phá sâu hơn")
st.info(
    "Chọn trang khác ở sidebar bên trái để xem chi tiết:\n\n"
    "- ** Kênh & Sản phẩm** — Sunburst, Treemap, top sản phẩm\n"
    "- ** Đội ngũ Sales** — Ranking sale, BDM/BDD, Sankey, scatter\n"
    "- ** Phân tích thời gian** — YoY, MoM, heatmap tuần × thứ\n"
    "- ** Chi tiết & Filter** — Tra cứu, download CSV/Excel"
)
