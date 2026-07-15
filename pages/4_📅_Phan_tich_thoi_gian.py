"""
Trang 4 — Phân tích theo thời gian
Charts: YoY bar / MoM combo / Heatmap week×day / Cumulative area / Contract expiry
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from lib.data import (
    COLORS, DATE_COL,
    apply_filters, apply_plotly_layout, empty_state, fmt_vnd,
    load_master_data, render_sidebar_filters,
)

st.set_page_config(page_title="Phân tích thời gian", page_icon="📅", layout="wide")
st.title("📅 Phân tích theo thời gian")
st.caption("Xu hướng, mùa vụ, so sánh cùng kỳ, dự báo tái tục.")

df_raw = load_master_data()
if df_raw.empty:
    empty_state("Chưa có data.")
    st.stop()

filters = render_sidebar_filters(df_raw)
df = apply_filters(df_raw, filters)
if df.empty:
    empty_state()
    st.stop()

# Ensure DATE_COL is datetime
df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
df = df[df[DATE_COL].notna()]

if df.empty:
    empty_state("Không có bản ghi có Ngày thanh toán hợp lệ.")
    st.stop()

# ============================================================================
# 4.1 YoY comparison — 12 tháng x 3 năm
# ============================================================================
st.markdown("### 📊 So sánh cùng kỳ (Year-over-Year)")

df_yoy = df.copy()
df_yoy["Year"] = df_yoy[DATE_COL].dt.year
df_yoy["Month"] = df_yoy[DATE_COL].dt.month
yoy = (df_yoy.groupby(["Year", "Month"], as_index=False)["Doanh thu trước thuế"].sum())

MONTH_LABEL = {i: f"T{i:02d}" for i in range(1, 13)}
yoy["Month_lbl"] = yoy["Month"].map(MONTH_LABEL)

if not yoy.empty:
    fig = px.bar(
        yoy, x="Month_lbl", y="Doanh thu trước thuế", color="Year",
        barmode="group", category_orders={"Month_lbl": list(MONTH_LABEL.values())},
        color_continuous_scale="Blues",
    )
    fig.update_xaxes(title="Tháng")
    fig.update_yaxes(title="Doanh thu (VNĐ)", tickformat=",")
    st.plotly_chart(apply_plotly_layout(fig, height=430), use_container_width=True)

    # Growth % table
    growth = yoy.pivot(index="Month_lbl", columns="Year", values="Doanh thu trước thuế")
    years = sorted(growth.columns.tolist())
    if len(years) >= 2:
        for i in range(1, len(years)):
            y_cur, y_prev = years[i], years[i-1]
            growth[f"YoY {y_cur} vs {y_prev}"] = (growth[y_cur] - growth[y_prev]) / growth[y_prev]
    growth = growth.round(0)
    st.markdown("**Bảng chi tiết (VNĐ) + growth rate:**")
    st.dataframe(
        growth,
        column_config={c: st.column_config.NumberColumn(str(c), format="%.0f ₫")
                       for c in years} | {
            f"YoY {years[i]} vs {years[i-1]}": st.column_config.NumberColumn(
                f"YoY {years[i]} vs {years[i-1]}", format="%.1f%%",
            ) for i in range(1, len(years))
        },
        use_container_width=True,
    )
else:
    empty_state()

st.divider()

# ============================================================================
# 4.2 MoM combo — bar + line
# ============================================================================
st.markdown("### 📈 MoM Trend: Doanh thu tháng + % tăng trưởng")

df_mom = df.copy()
df_mom["Month_str"] = df_mom[DATE_COL].dt.to_period("M").astype(str)
mom = df_mom.groupby("Month_str", as_index=False)["Doanh thu trước thuế"].sum().sort_values("Month_str")
mom["MoM_pct"] = mom["Doanh thu trước thuế"].pct_change() * 100

if not mom.empty:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=mom["Month_str"], y=mom["Doanh thu trước thuế"],
        name="Doanh thu",
        marker_color="#1F77B4",
        hovertemplate="Tháng: %{x}<br>DT: %{y:,.0f} ₫<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=mom["Month_str"], y=mom["MoM_pct"],
        name="MoM %", mode="lines+markers",
        line=dict(color="#E74C3C", width=2),
        marker=dict(size=8),
        hovertemplate="Tháng: %{x}<br>MoM: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.update_xaxes(title="")
    fig.update_yaxes(title_text="Doanh thu (VNĐ)", tickformat=",", secondary_y=False)
    fig.update_yaxes(title_text="MoM %", secondary_y=True, ticksuffix="%")
    st.plotly_chart(apply_plotly_layout(fig, height=420), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 4.3 Heatmap: Ngày trong tuần × Tuần trong năm
# ============================================================================
st.markdown("### 🔥 Heatmap: Ngày trong tuần × Tuần trong năm")

metric_choice = st.radio(
    "Chỉ số",
    ["Doanh thu", "Số HĐ", "EST Bonus"],
    horizontal=True, key="hm_metric",
)
metric_map = {
    "Doanh thu": ("Doanh thu trước thuế", "sum"),
    "Số HĐ": ("Số hợp đồng", "nunique"),
    "EST Bonus": ("EST_Bonus", "sum"),
}
metric_col, metric_agg = metric_map[metric_choice]

df_hm = df.copy()
df_hm["dow"] = df_hm[DATE_COL].dt.dayofweek  # 0 = T2
df_hm["week"] = df_hm[DATE_COL].dt.isocalendar().week
df_hm["year"] = df_hm[DATE_COL].dt.year

# Filter year (nếu có nhiều năm, cho user chọn)
years_avail = sorted(df_hm["year"].dropna().unique().tolist())
if len(years_avail) > 1:
    year_pick = st.selectbox("Năm", years_avail, index=len(years_avail) - 1, key="hm_year")
    df_hm = df_hm[df_hm["year"] == year_pick]

pivot = df_hm.groupby(["dow", "week"], as_index=False).agg(val=(metric_col, metric_agg))
pivot_mx = pivot.pivot(index="dow", columns="week", values="val").fillna(0)

if not pivot_mx.empty:
    DOW_LABEL = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    fig = go.Figure(data=go.Heatmap(
        z=pivot_mx.values,
        x=[f"W{w}" for w in pivot_mx.columns],
        y=[DOW_LABEL[d] if d < 7 else str(d) for d in pivot_mx.index],
        colorscale="YlOrRd",
        colorbar=dict(title=metric_choice),
        hovertemplate="Tuần %{x}<br>%{y}<br>" + metric_choice + ": %{z:,.0f}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(apply_plotly_layout(fig, height=380), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 4.4 Cumulative revenue by Source
# ============================================================================
st.markdown("### 📈 Doanh thu cộng dồn theo thời gian")

df_cum = df.copy().sort_values(DATE_COL)
df_cum["date_only"] = df_cum[DATE_COL].dt.date
by_day = df_cum.groupby(["date_only", "Source"], as_index=False)["Doanh thu trước thuế"].sum()
by_day = by_day.sort_values("date_only")
by_day["cum"] = by_day.groupby("Source")["Doanh thu trước thuế"].cumsum()

if not by_day.empty:
    fig = px.area(
        by_day, x="date_only", y="cum", color="Source",
        color_discrete_map=COLORS, line_shape="spline",
    )
    fig.update_yaxes(title="Doanh thu cộng dồn (VNĐ)", tickformat=",")
    fig.update_xaxes(title="")
    st.plotly_chart(apply_plotly_layout(fig, height=450), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 4.5 Contract expiry — HĐ sắp hết hạn
# ============================================================================
st.markdown("### ⏰ HĐ sắp hết hạn (dùng cho tái tục)")

if "Ngày kết thúc" in df.columns:
    today = pd.Timestamp.now().normalize()
    df_exp = df.copy()
    df_exp["Ngày kết thúc"] = pd.to_datetime(df_exp["Ngày kết thúc"], errors="coerce")
    df_exp["days_to_expiry"] = (df_exp["Ngày kết thúc"] - today).dt.days

    # Chỉ show HĐ có ngày kết thúc trong 60 ngày tới hoặc đã hết hạn trong 30 ngày qua
    df_exp_view = df_exp[(df_exp["days_to_expiry"] >= -30) & (df_exp["days_to_expiry"] <= 90)].copy()

    if not df_exp_view.empty:
        # Bin days_to_expiry vào 4 nhóm
        def _bin(x):
            if x < 0: return "Đã hết hạn (30d qua)"
            if x < 15: return "Hết trong 15 ngày"
            if x < 30: return "Hết trong 15-30 ngày"
            if x < 60: return "Hết trong 30-60 ngày"
            return "Hết trong 60-90 ngày"
        df_exp_view["bucket"] = df_exp_view["days_to_expiry"].apply(_bin)

        bucket_order = ["Đã hết hạn (30d qua)", "Hết trong 15 ngày",
                        "Hết trong 15-30 ngày", "Hết trong 30-60 ngày",
                        "Hết trong 60-90 ngày"]
        counts = (df_exp_view.groupby(["bucket", "Loại bảo hiểm"], as_index=False)
                             .agg(So_HD=("Số hợp đồng", "nunique"),
                                  Doanh_thu=("Doanh thu trước thuế", "sum")))

        c_left, c_right = st.columns(2)
        with c_left:
            fig = px.bar(
                counts, x="bucket", y="So_HD", color="Loại bảo hiểm",
                color_discrete_map=COLORS,
                category_orders={"bucket": bucket_order},
            )
            fig.update_xaxes(title="", tickangle=-15)
            fig.update_yaxes(title="Số HĐ")
            st.plotly_chart(apply_plotly_layout(fig, "Số HĐ theo cửa sổ hết hạn", 400), use_container_width=True)

        with c_right:
            fig = px.bar(
                counts, x="bucket", y="Doanh_thu", color="Loại bảo hiểm",
                color_discrete_map=COLORS,
                category_orders={"bucket": bucket_order},
            )
            fig.update_xaxes(title="", tickangle=-15)
            fig.update_yaxes(title="Doanh thu (VNĐ)", tickformat=",")
            st.plotly_chart(apply_plotly_layout(fig, "Doanh thu tương ứng", 400), use_container_width=True)

        # HĐ khẩn cấp: hết trong 15 ngày
        urgent = df_exp_view[df_exp_view["days_to_expiry"].between(0, 14)].copy()
        if not urgent.empty:
            urgent_view = urgent[["Số hợp đồng", "Tên NĐBH", "Loại bảo hiểm",
                                  "Sản phẩm", "Nhà BH", "Họ tên sale",
                                  "Ngày kết thúc", "days_to_expiry",
                                  "Phí BH (VNĐ)"]].sort_values("days_to_expiry")
            st.markdown(f"**🚨 {len(urgent_view)} HĐ hết hạn trong 15 ngày tới:**")
            st.dataframe(
                urgent_view.rename(columns={"days_to_expiry": "Số ngày còn"}),
                column_config={
                    "Ngày kết thúc": st.column_config.DateColumn("Ngày kết thúc", format="DD/MM/YYYY"),
                    "Số ngày còn": st.column_config.NumberColumn("Số ngày còn", format="%d"),
                    "Phí BH (VNĐ)": st.column_config.NumberColumn("Phí BH", format="%.0f ₫"),
                },
                hide_index=True,
                use_container_width=True,
                height=350,
            )
    else:
        empty_state("Không có HĐ nào sắp hết hạn trong 90 ngày tới hoặc vừa hết hạn trong 30 ngày qua.")
else:
    st.info("Không có cột `Ngày kết thúc`")
