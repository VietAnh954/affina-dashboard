"""
================================================================================
 TRANG 10 — KPI COMPETITION: CLB Tinh Hoa Affina 2026-2027
================================================================================
Chương trình thi đua: 01/04/2026 - 31/03/2027
13 suất du lịch Trung Quốc

Cấp bậc:
  - Giám Đốc (BDD/SD-RMD/TSA Manager): Top 3 KPI QL, >=70% x 3 tháng, TB >=50%
  - Trưởng Phòng (BDM/SM-RMM/TSA TL):  Top 5 KPI QL, >=70% x 3 tháng, TB >=50%
  - Chuyên Viên (CVKD/AG-RMC/CTV TSA):  Top 5 điểm quy đổi

Tính điểm Chuyên Viên:
  - Mỗi 5 triệu doanh thu cá nhân = 1 điểm
  - Mỗi 5 triệu doanh thu từ người giới thiệu = 1 điểm
  - Hạng 1 tháng: +10 điểm, Hạng 2: +5, Hạng 3: +3

LƯU Ý: KHÔNG hiển thị Affina_Revenue trong trang này.
================================================================================
"""
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.auth import require_auth
from lib.data import (
    COLORS, DATE_COL,
    apply_plotly_layout, empty_state,
    fmt_num, fmt_vnd,
    load_master_data,
)

st.set_page_config(page_title="KPI Competition", layout="wide")

# ── Auth ──
require_auth("kpi", "KPI Competition — CLB Tinh Hoa Affina")

from lib.theme import inject_css
inject_css()


# Theme: dùng chung hồng pastel với các trang khác (dark theme đã bỏ)


# ============================================================================
# CONFIG
# ============================================================================
COMP_START = pd.Timestamp("2026-04-01")
COMP_END   = pd.Timestamp("2027-03-31")
POINTS_PER = 5_000_000  # 5 triệu = 1 điểm

# Cột KHÔNG được hiển thị (yêu cầu business)
HIDDEN_COLS = {"Affina_Revenue", "Affina_rate_bonus"}

# Mapping chức danh → cấp thi đua
LEVEL_MAP = {
    # Giám Đốc level
    "BDD": "Giám Đốc",
    "SD":  "Giám Đốc", "RMD": "Giám Đốc",
    "TSA Manager": "Giám Đốc",
    # Trưởng Phòng level
    "BDM": "Trưởng Phòng",
    "SM":  "Trưởng Phòng", "RMM": "Trưởng Phòng",
    "TSA Team Leader": "Trưởng Phòng",
    # Chuyên Viên level
    "CTV": "Chuyên Viên",
    "CVKD": "Chuyên Viên",
    "AG":  "Chuyên Viên", "RMC": "Chuyên Viên",
    "CTV TSA": "Chuyên Viên",
    "TSA": "Chuyên Viên",
}

TOP_N = {"Giám Đốc": 3, "Trưởng Phòng": 5, "Chuyên Viên": 5}


# ============================================================================
# HELPERS
# ============================================================================
def _classify_level(chuc_danh: str) -> str:
    if pd.isna(chuc_danh):
        return "Chuyên Viên"
    cd = str(chuc_danh).strip()
    if cd in LEVEL_MAP:
        return LEVEL_MAP[cd]
    cd_upper = cd.upper()
    if "BDD" in cd_upper or "GIÁM ĐỐC" in cd_upper:
        return "Giám Đốc"
    if "BDM" in cd_upper or "TRƯỞNG" in cd_upper:
        return "Trưởng Phòng"
    return "Chuyên Viên"


def _compute_points(revenue: float) -> int:
    """Mỗi 5 triệu = 1 điểm."""
    if pd.isna(revenue) or revenue <= 0:
        return 0
    return int(revenue // POINTS_PER)


def _monthly_rank_bonus(rank: int) -> int:
    """Hạng 1: +10, Hạng 2: +5, Hạng 3: +3."""
    if rank == 1: return 10
    if rank == 2: return 5
    if rank == 3: return 3
    return 0


# ============================================================================
# MAIN
# ============================================================================
st.title("KPI Competition — CLB Tinh Hoa Affina")
st.markdown(
    "**Chu kỳ thi đua:** 01/04/2026 - 31/03/2027  |  "
    "**Giải thưởng:** 13 suất du lịch Trung Quốc  |  "
    "**Công bố:** Tháng 04/2027"
)

# ── Load data ──
df_all = load_master_data()
if df_all.empty:
    st.warning("Chưa có dữ liệu.")
    st.stop()

# Filter theo chu kỳ thi đua
df_all[DATE_COL] = pd.to_datetime(df_all[DATE_COL], errors="coerce")
df = df_all[(df_all[DATE_COL] >= COMP_START) & (df_all[DATE_COL] <= COMP_END)].copy()

if df.empty:
    st.warning(
        f"Chưa có dữ liệu trong chu kỳ thi đua ({COMP_START.strftime('%d/%m/%Y')} - {COMP_END.strftime('%d/%m/%Y')}). "
        f"Dữ liệu sẽ xuất hiện khi có HĐ từ 01/04/2026."
    )
    st.stop()

# Bỏ cột cấm
for col in HIDDEN_COLS:
    if col in df.columns:
        df = df.drop(columns=[col])

# Classify level
if "Chức danh" in df.columns:
    df["Cấp thi đua"] = df["Chức danh"].apply(_classify_level)
else:
    df["Cấp thi đua"] = "Chuyên Viên"

df["month"] = df[DATE_COL].dt.to_period("M")

# ── Sidebar filter ──
st.sidebar.markdown("---")
st.sidebar.markdown("### Bộ lọc KPI")

level_filter = st.sidebar.radio(
    "Cấp thi đua",
    options=["Tất cả", "Giám Đốc", "Trưởng Phòng", "Chuyên Viên"],
    index=0,
    key="kpi_level",
)
if level_filter != "Tất cả":
    df = df[df["Cấp thi đua"] == level_filter]

if "Source" in df.columns:
    sources = sorted(df["Source"].dropna().unique())
    sel_src = st.sidebar.multiselect("Source", options=sources, default=sources, key="kpi_src")
    if sel_src:
        df = df[df["Source"].isin(sel_src)]

if df.empty:
    empty_state("Không có dữ liệu sau filter.")
    st.stop()

# ============================================================================
# 1. TIẾN ĐỘ CHU KỲ
# ============================================================================
st.markdown("### Tiến độ chu kỳ thi đua")

today = pd.Timestamp.now().normalize()
if today < COMP_START:
    days_elapsed = 0
    pct_elapsed = 0
elif today > COMP_END:
    days_elapsed = (COMP_END - COMP_START).days
    pct_elapsed = 100
else:
    days_elapsed = (today - COMP_START).days
    pct_elapsed = days_elapsed / (COMP_END - COMP_START).days * 100

days_remaining = max(0, (COMP_END - today).days)
months_elapsed = min(12, max(0, (today.year - COMP_START.year) * 12 + today.month - COMP_START.month))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ngày đã qua", f"{days_elapsed} / {(COMP_END - COMP_START).days}")
c2.metric("Ngày còn lại", fmt_num(days_remaining))
c3.metric("Tháng đã qua", f"{months_elapsed} / 12")
c4.metric("Tiến độ", f"{pct_elapsed:.1f}%")

# Progress bar
st.progress(min(pct_elapsed / 100, 1.0))

st.divider()

# ============================================================================
# 2. BẢNG XẾP HẠNG TỔNG HỢP
# ============================================================================
st.markdown("### Bảng xếp hạng")

sale_col = "Họ tên sale" if "Họ tên sale" in df.columns else "Họ tên"
if sale_col not in df.columns:
    st.error("Không tìm thấy cột tên sale.")
    st.stop()

# Tổng doanh thu per sale
ranking = df.groupby([sale_col], as_index=False).agg(
    chuc_danh=("Chức danh", "first") if "Chức danh" in df.columns else (sale_col, "count"),
    cap_thi_dua=("Cấp thi đua", "first"),
    source=("Source", "first") if "Source" in df.columns else (sale_col, "count"),
    channel=("Channel", "first") if "Channel" in df.columns else (sale_col, "count"),
    total_revenue=("Doanh thu trước thuế", "sum"),
    n_hd=("Số hợp đồng", "nunique") if "Số hợp đồng" in df.columns else (sale_col, "count"),
    n_months=(DATE_COL, lambda x: x.dt.to_period("M").nunique()),
)

# Tính điểm quy đổi (chỉ cho Chuyên Viên, nhưng show cho mọi cấp)
ranking["Điểm quy đổi"] = ranking["total_revenue"].apply(_compute_points)

# Monthly rank bonus
monthly_rev = df.groupby([sale_col, "month"])["Doanh thu trước thuế"].sum().reset_index()
monthly_rev["month_rank"] = monthly_rev.groupby("month")["Doanh thu trước thuế"].rank(ascending=False, method="min")
monthly_rev["rank_bonus"] = monthly_rev["month_rank"].apply(_monthly_rank_bonus)
bonus_total = monthly_rev.groupby(sale_col)["rank_bonus"].sum().reset_index()
bonus_total.columns = [sale_col, "Bonus tháng"]

# Đếm tháng đạt top 3
top3_months = monthly_rev[monthly_rev["month_rank"] <= 3].groupby(sale_col).size().reset_index(name="Tháng top 3")

ranking = ranking.merge(bonus_total, on=sale_col, how="left")
ranking = ranking.merge(top3_months, on=sale_col, how="left")
ranking["Bonus tháng"] = ranking["Bonus tháng"].fillna(0).astype(int)
ranking["Tháng top 3"] = ranking["Tháng top 3"].fillna(0).astype(int)
ranking["Tổng điểm"] = ranking["Điểm quy đổi"] + ranking["Bonus tháng"]

# Sort + rank
ranking = ranking.sort_values("Tổng điểm", ascending=False).reset_index(drop=True)
ranking.insert(0, "Hạng", range(1, len(ranking) + 1))

# Highlight zone (top N theo cấp)
def _in_prize_zone(row):
    cap = row["cap_thi_dua"]
    top_n = TOP_N.get(cap, 5)
    # Rank within cấp
    cap_df = ranking[ranking["cap_thi_dua"] == cap]
    cap_rank = cap_df["Tổng điểm"].rank(ascending=False, method="min")
    idx = cap_df.index.get_loc(row.name) if row.name in cap_df.index else 999
    return idx < top_n

# Display columns
disp = ranking[[
    "Hạng", sale_col, "cap_thi_dua", "source", "channel",
    "n_hd", "total_revenue", "Điểm quy đổi", "Bonus tháng", "Tổng điểm",
    "Tháng top 3", "n_months"
]].copy()
disp.columns = [
    "Hạng", "Họ tên", "Cấp", "Source", "Channel",
    "Số HĐ", "Tổng doanh thu", "Điểm QĐ", "Bonus rank", "Tổng điểm",
    "Tháng top 3", "Tháng active"
]
disp["Tổng doanh thu"] = disp["Tổng doanh thu"].apply(lambda v: fmt_vnd(v, short=True))

# Tab chia theo cấp
tab_all, tab_gd, tab_tp, tab_cv = st.tabs(["Tất cả", "Giám Đốc (Top 3)", "Trưởng Phòng (Top 5)", "Chuyên Viên (Top 5)"])

with tab_all:
    st.dataframe(disp, hide_index=True, use_container_width=True, height=450)

with tab_gd:
    gd = disp[disp["Cấp"] == "Giám Đốc"].reset_index(drop=True)
    gd["Hạng"] = range(1, len(gd) + 1)
    if not gd.empty:
        st.dataframe(gd.head(20), hide_index=True, use_container_width=True)
        st.success(f"Vùng giải thưởng: Top **3** — hiện có **{min(3, len(gd))}** người đủ điều kiện xét")
    else:
        empty_state("Không có Giám Đốc trong dữ liệu.")

with tab_tp:
    tp = disp[disp["Cấp"] == "Trưởng Phòng"].reset_index(drop=True)
    tp["Hạng"] = range(1, len(tp) + 1)
    if not tp.empty:
        st.dataframe(tp.head(20), hide_index=True, use_container_width=True)
        st.success(f"Vùng giải thưởng: Top **5** — hiện có **{min(5, len(tp))}** người đủ điều kiện xét")
    else:
        empty_state("Không có Trưởng Phòng.")

with tab_cv:
    cv = disp[disp["Cấp"] == "Chuyên Viên"].reset_index(drop=True)
    cv["Hạng"] = range(1, len(cv) + 1)
    if not cv.empty:
        st.dataframe(cv.head(30), hide_index=True, use_container_width=True)
        st.success(f"Vùng giải thưởng: Top **5** — hiện có **{min(5, len(cv))}** người đủ điều kiện xét")
    else:
        empty_state("Không có Chuyên Viên.")

st.divider()

# ============================================================================
# 3. TOP 10 BAR CHART + KHOẢNG CÁCH
# ============================================================================
st.markdown("### Top 10 — Tổng điểm + Khoảng cách")
col_bar, col_gap = st.columns([3, 2])

with col_bar:
    top10 = ranking.head(10)
    if not top10.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top10[sale_col], x=top10["Điểm quy đổi"],
            name="Điểm doanh thu",
            orientation="h",
            marker_color="#B44BC8",
            text=top10["Điểm quy đổi"], textposition="inside",
        ))
        fig.add_trace(go.Bar(
            y=top10[sale_col], x=top10["Bonus tháng"],
            name="Bonus rank tháng",
            orientation="h",
            marker_color="#E85BD8",
            text=top10["Bonus tháng"], textposition="inside",
        ))
        fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed"))
        st.plotly_chart(apply_plotly_layout(fig, title="Top 10 tổng điểm (stacked)", height=400),
                        use_container_width=True)

with col_gap:
    st.markdown("**Khoảng cách đến vùng giải thưởng**")
    for cap, top_n in TOP_N.items():
        cap_df = ranking[ranking["cap_thi_dua"] == cap].head(top_n + 3)
        if len(cap_df) > top_n:
            threshold = cap_df.iloc[top_n - 1]["Tổng điểm"]
            first_out = cap_df.iloc[top_n] if len(cap_df) > top_n else None
            if first_out is not None:
                gap = threshold - first_out["Tổng điểm"]
                gap_revenue = gap * POINTS_PER
                st.markdown(
                    f"**{cap}** (Top {top_n}):  \n"
                    f"Ngưỡng vào giải: **{int(threshold)} điểm**  \n"
                    f"Người đầu tiên ngoài giải cách **{int(gap)} điểm** "
                    f"(~ {fmt_vnd(gap_revenue, short=True)} doanh thu)"
                )
        elif len(cap_df) > 0:
            st.markdown(f"**{cap}** (Top {top_n}): Chưa đủ người để so sánh")
        st.markdown("")

st.divider()

# ============================================================================
# 4. TIẾN TRÌNH ĐIỂM THEO THÁNG (line chart)
# ============================================================================
st.markdown("### Tiến trình tích lũy điểm theo tháng")

# Top 10 sale — cumulative points per month
top10_names = ranking.head(10)[sale_col].tolist()
if top10_names:
    monthly_top = monthly_rev[monthly_rev[sale_col].isin(top10_names)].copy()
    monthly_top["points"] = monthly_top["Doanh thu trước thuế"].apply(_compute_points)
    monthly_top["total_points"] = monthly_top["points"] + monthly_top["rank_bonus"]
    monthly_top["month_ts"] = monthly_top["month"].dt.to_timestamp()

    # Cumulative
    monthly_top = monthly_top.sort_values(["month_ts", sale_col])
    monthly_top["cum_points"] = monthly_top.groupby(sale_col)["total_points"].cumsum()

    fig = px.line(
        monthly_top, x="month_ts", y="cum_points", color=sale_col,
        markers=True,
        labels={"month_ts": "Tháng", "cum_points": "Tổng điểm tích lũy", sale_col: "Sale"},
    )
    fig.update_xaxes(dtick="M1", tickformat="%m/%Y")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(apply_plotly_layout(fig, title="", height=420), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 5. HEATMAP RANK THÁNG
# ============================================================================
st.markdown("### Xếp hạng theo tháng — Ai dẫn đầu mỗi tháng?")

n_show = st.slider("Số sale hiển thị", min_value=5, max_value=30, value=10, key="kpi_heatmap_n")

top_n_names = ranking.head(n_show)[sale_col].tolist()
if top_n_names:
    heat_data = monthly_rev[monthly_rev[sale_col].isin(top_n_names)].copy()
    heat_data["month_str"] = heat_data["month"].astype(str)
    heat_pivot = heat_data.pivot_table(
        index=sale_col, columns="month_str", values="month_rank", aggfunc="first"
    )
    # Sắp xếp theo tổng rank (thấp = tốt)
    heat_pivot = heat_pivot.loc[heat_pivot.mean(axis=1).sort_values().index]

    fig = px.imshow(
        heat_pivot.values,
        x=heat_pivot.columns.tolist(),
        y=heat_pivot.index.tolist(),
        aspect="auto",
        color_continuous_scale=["#5FBFA0", "#FDF2FB", "#E8738F"],
        text_auto=".0f",
        labels=dict(color="Hạng"),
    )
    fig.update_layout(height=max(300, 35 * n_show))
    st.plotly_chart(apply_plotly_layout(fig, title="Hạng mỗi tháng (1 = dẫn đầu, xanh = tốt, hồng = thấp)"),
                    use_container_width=True)
    st.caption("Xanh mint = hạng cao, hồng = hạng thấp. Ô trống = không có HĐ tháng đó.")

st.divider()

# ============================================================================
# 6. SO SÁNH 1:1
# ============================================================================
st.markdown("### So sánh 1 vs 1")

all_sales = ranking[sale_col].tolist()
if len(all_sales) >= 2:
    col1, col2 = st.columns(2)
    with col1:
        sale_a = st.selectbox("Sale A", options=all_sales, index=0, key="kpi_a")
    with col2:
        default_b = 1 if len(all_sales) > 1 else 0
        sale_b = st.selectbox("Sale B", options=all_sales, index=default_b, key="kpi_b")

    if sale_a and sale_b and sale_a != sale_b:
        row_a = ranking[ranking[sale_col] == sale_a].iloc[0]
        row_b = ranking[ranking[sale_col] == sale_b].iloc[0]

        metrics = ["Tổng điểm", "Điểm quy đổi", "Bonus tháng", "total_revenue", "n_hd", "Tháng top 3"]
        labels  = ["Tổng điểm", "Điểm QĐ",      "Bonus rank",  "Doanh thu",     "Số HĐ", "Tháng top 3"]

        c1, c2, c3 = st.columns([2, 1, 2])
        with c1:
            st.markdown(f"**{sale_a}**")
            st.caption(f"Hạng {int(row_a['Hạng'])} | {row_a['cap_thi_dua']}")
        with c2:
            st.markdown("<div style='text-align:center'>vs</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"**{sale_b}**")
            st.caption(f"Hạng {int(row_b['Hạng'])} | {row_b['cap_thi_dua']}")

        # Radar chart
        values_a = [float(row_a[m]) for m in metrics]
        values_b = [float(row_b[m]) for m in metrics]
        # Normalize to 0-1 for radar
        max_vals = [max(a, b, 1) for a, b in zip(values_a, values_b)]
        norm_a = [a / m for a, m in zip(values_a, max_vals)]
        norm_b = [b / m for b, m in zip(values_b, max_vals)]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=norm_a + [norm_a[0]],
            theta=labels + [labels[0]],
            fill="toself", name=sale_a,
            fillcolor="rgba(180, 75, 200, 0.2)",
            line_color="#B44BC8",
        ))
        fig.add_trace(go.Scatterpolar(
            r=norm_b + [norm_b[0]],
            theta=labels + [labels[0]],
            fill="toself", name=sale_b,
            fillcolor="rgba(240, 110, 194, 0.2)",
            line_color="#F06EC2",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1.1])),
            height=380,
        )
        st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

        # Monthly comparison
        monthly_ab = monthly_rev[monthly_rev[sale_col].isin([sale_a, sale_b])].copy()
        monthly_ab["month_ts"] = monthly_ab["month"].dt.to_timestamp()
        monthly_ab["points"] = monthly_ab["Doanh thu trước thuế"].apply(_compute_points) + monthly_ab["rank_bonus"]

        if not monthly_ab.empty:
            fig2 = px.bar(
                monthly_ab, x="month_ts", y="points", color=sale_col,
                barmode="group",
                color_discrete_map={sale_a: "#B44BC8", sale_b: "#F06EC2"},
                labels={"month_ts": "Tháng", "points": "Điểm"},
            )
            fig2.update_xaxes(dtick="M1", tickformat="%m/%Y")
            st.plotly_chart(apply_plotly_layout(fig2, title="Điểm theo tháng", height=320),
                            use_container_width=True)
    elif sale_a == sale_b:
        st.info("Chọn 2 sale khác nhau để so sánh.")

st.divider()

# ============================================================================
# 7. DỰ BÁO — Tốc độ tích điểm
# ============================================================================
st.markdown("### Dự báo cuối chu kỳ (ước tính)")

if months_elapsed > 0 and not ranking.empty:
    ranking["Tốc độ điểm/tháng"] = (ranking["Tổng điểm"] / max(months_elapsed, 1)).round(1)
    ranking["Dự báo cuối kỳ"] = (ranking["Tốc độ điểm/tháng"] * 12).round(0).astype(int)

    forecast_df = ranking.head(15)[[sale_col, "cap_thi_dua", "Tổng điểm", "Tốc độ điểm/tháng", "Dự báo cuối kỳ"]].copy()
    forecast_df.columns = ["Họ tên", "Cấp", "Điểm hiện tại", "Tốc độ/tháng", "Dự báo cuối kỳ (12 tháng)"]
    forecast_df.insert(0, "Hạng", range(1, len(forecast_df) + 1))
    st.dataframe(forecast_df, hide_index=True, use_container_width=True)

    st.caption(
        "Dự báo dựa trên giả định tốc độ tích điểm giữ nguyên. "
        "Thực tế có thể thay đổi do chương trình mới, mùa vụ, thay đổi nhân sự."
    )
else:
    st.info("Cần ít nhất 1 tháng dữ liệu trong chu kỳ thi đua.")

st.divider()

# ============================================================================
# 8. PHÂN PHỐI ĐIỂM
# ============================================================================
st.markdown("### Phân phối điểm — Mức độ cạnh tranh")

if len(ranking) >= 5:
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=ranking["Tổng điểm"],
        nbinsx=30,
        marker_color="#B44BC8",
        opacity=0.75,
    ))
    # Vẽ đường threshold cho từng cấp
    for cap, top_n in TOP_N.items():
        cap_df = ranking[ranking["cap_thi_dua"] == cap]
        if len(cap_df) >= top_n:
            threshold = cap_df.head(top_n).iloc[-1]["Tổng điểm"]
            fig.add_vline(
                x=threshold, line_dash="dash", line_color="#E8738F",
                annotation_text=f"{cap}: {int(threshold)} điểm",
                annotation_position="top",
            )
    fig.update_layout(
        xaxis_title="Tổng điểm",
        yaxis_title="Số sale",
        showlegend=False,
        height=350,
    )
    st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)
    st.caption("Đường đứt = ngưỡng vào vùng giải thưởng từng cấp. Sale nằm bên phải đường = đang trong zone.")

st.divider()

# ============================================================================
# FOOTER
# ============================================================================
st.markdown(
    "---\n"
    "*Dữ liệu cập nhật hàng ngày. Kết quả chính thức do Ban Tổ chức công bố tháng 04/2027. "
    "Bảng xếp hạng này chỉ mang tính chất tham khảo.*"
)
