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

from lib.auth import require_auth, render_user_info
from lib.data import (
    COLORS, DATE_COL,
    apply_plotly_layout, empty_state,
    fmt_num, fmt_vnd,
    load_master_data,
)

st.set_page_config(page_title="KPI Competition", layout="wide")

# ── Auth ──
require_auth("kpi", "KPI Competition — CLB Tinh Hoa Affina")
render_user_info()

from lib.theme import inject_css, render_header
inject_css()
render_header()


# ============================================================================
# CONFIG
# ============================================================================
COMP_START = pd.Timestamp("2026-04-01")
COMP_END   = pd.Timestamp("2027-03-31")
POINTS_PER = 5_000_000  # 5 triệu = 1 điểm

HIDDEN_COLS = {"Affina_Revenue", "Affina_rate_bonus"}

LEVEL_MAP = {
    "BDD": "Giam Doc", "SD": "Giam Doc", "RMD": "Giam Doc",
    "TSA Manager": "Giam Doc",
    "BDM": "Truong Phong", "SM": "Truong Phong", "RMM": "Truong Phong",
    "TSA Team Leader": "Truong Phong",
    "CTV": "Chuyen Vien", "CVKD": "Chuyen Vien",
    "AG": "Chuyen Vien", "RMC": "Chuyen Vien",
    "CTV TSA": "Chuyen Vien", "TSA": "Chuyen Vien",
}

TOP_N = {"Giam Doc": 3, "Truong Phong": 5, "Chuyen Vien": 5}

QUARTERS = {
    "Q1 (04-06/2026)": (pd.Timestamp("2026-04-01"), pd.Timestamp("2026-06-30")),
    "Q2 (07-09/2026)": (pd.Timestamp("2026-07-01"), pd.Timestamp("2026-09-30")),
    "Q3 (10-12/2026)": (pd.Timestamp("2026-10-01"), pd.Timestamp("2026-12-31")),
    "Q4 (01-03/2027)": (pd.Timestamp("2027-01-01"), pd.Timestamp("2027-03-31")),
}


# ============================================================================
# HELPERS
# ============================================================================
def _classify_level(chuc_danh: str) -> str:
    if pd.isna(chuc_danh):
        return "Chuyen Vien"
    cd = str(chuc_danh).strip()
    if cd in LEVEL_MAP:
        return LEVEL_MAP[cd]
    cd_upper = cd.upper()
    if "BDD" in cd_upper or "GIAM DOC" in cd_upper:
        return "Giam Doc"
    if "BDM" in cd_upper or "TRUONG" in cd_upper:
        return "Truong Phong"
    return "Chuyen Vien"


def _compute_points(revenue: float) -> int:
    if pd.isna(revenue) or revenue <= 0:
        return 0
    return int(revenue // POINTS_PER)


def _monthly_rank_bonus(rank: int) -> int:
    if rank == 1: return 10
    if rank == 2: return 5
    if rank == 3: return 3
    return 0


def _get_current_quarter() -> str:
    today = pd.Timestamp.now().normalize()
    for qname, (qs, qe) in QUARTERS.items():
        if qs <= today <= qe:
            return qname
    return list(QUARTERS.keys())[-1]


def _is_quarter_closed(qname: str) -> bool:
    _, qe = QUARTERS[qname]
    return pd.Timestamp.now().normalize() > qe


# ============================================================================
# MAIN
# ============================================================================
st.title("KPI Competition — CLB Tinh Hoa Affina")
st.markdown(
    "**Chu ky thi dua:** 01/04/2026 - 31/03/2027  |  "
    "**Giai thuong:** 13 suat du lich Trung Quoc  |  "
    "**Cong bo:** Thang 04/2027"
)

# ============================================================================
# THE LE THI DUA (expander)
# ============================================================================
with st.expander("**THE LE THI DUA — CLB Tinh Hoa Affina 2026-2027**", expanded=False):
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Doi tuong thi dua")
        st.markdown("""
| Cap bac | Kenh Core | Kenh Neo | Kenh TSA | So luong giai |
|---------|-----------|----------|----------|--------------|
| Giam Doc PTKD | BDD | SD/RMD | TSA Manager | **03 suat** |
| Truong Phong PTKD | BDM | SM/RMM | TSA Team Leader | **05 suat** |
| Chuyen Vien KD | CVKD | AG/RMC | CTV TSA | **05 suat** |
""")
        st.markdown("""
**Luu y:**
- Cap Truong Phong va Giam Doc co the thi dua cung hang hoac thi dua voi Chuyen Vien KD.
- Moi ca nhan chi nhan toi da **01 ve thuong**. Truong hop dat tieu chuan o 02 nhom thi nhan thuong theo chuc danh cao nhat.
""")

    with col_right:
        st.markdown("#### Tieu chi xet thuong")
        st.markdown("""
**Giam Doc** (Top 3):
- Top 03 co ket qua KPI quan ly cao nhat
- Dat >= 70% KPI hang thang trong it nhat 03 thang
- Tong ket qua trung binh cac thang >= 50% KPI

**Truong Phong** (Top 5):
- Top 05 co ket qua KPI quan ly cao nhat
- Dat >= 70% KPI hang thang trong it nhat 03 thang
- Tong ket qua trung binh cac thang >= 50%

**Chuyen Vien KD** (Top 5):
- Top 05 co tong diem quy doi cao nhat
- Moi 5 trieu dong doanh thu = **1 diem**
- Bonus rank hang thang: Hang 1 = +10, Hang 2 = +5, Hang 3 = +3
- Tinh toan thuc hien **tung thang**
""")

    st.markdown("**Thoi gian:** 01/04/2026 - 31/03/2027  |  **Cong bo ket qua:** Thang 04/2027  |  **Trao thuong:** Du kien Quy 2-3/2027")

st.divider()

# ── Load data ──
df_all = load_master_data()
if df_all.empty:
    st.warning("Chua co du lieu.")
    st.stop()

df_all[DATE_COL] = pd.to_datetime(df_all[DATE_COL], errors="coerce")
df = df_all[(df_all[DATE_COL] >= COMP_START) & (df_all[DATE_COL] <= COMP_END)].copy()

if df.empty:
    st.warning(
        f"Chua co du lieu trong chu ky thi dua ({COMP_START.strftime('%d/%m/%Y')} - {COMP_END.strftime('%d/%m/%Y')})."
    )
    st.stop()

for col in HIDDEN_COLS:
    if col in df.columns:
        df = df.drop(columns=[col])

if "Chức danh" in df.columns:
    df["Cap thi dua"] = df["Chức danh"].apply(_classify_level)
else:
    df["Cap thi dua"] = "Chuyen Vien"

df["month"] = df[DATE_COL].dt.to_period("M")

sale_col = "Họ tên sale" if "Họ tên sale" in df.columns else "Họ tên"
if sale_col not in df.columns:
    st.error("Khong tim thay cot ten sale.")
    st.stop()

# ── Sidebar filter ──
st.sidebar.markdown("---")
st.sidebar.markdown("### Bo loc KPI")

level_filter = st.sidebar.radio(
    "Cap thi dua",
    options=["Tat ca", "Giam Doc", "Truong Phong", "Chuyen Vien"],
    index=0,
    key="kpi_level",
)
if level_filter != "Tat ca":
    df = df[df["Cap thi dua"] == level_filter]

if "Source" in df.columns:
    sources = sorted(df["Source"].dropna().unique())
    sel_src = st.sidebar.multiselect("Source", options=sources, default=sources, key="kpi_src")
    if sel_src:
        df = df[df["Source"].isin(sel_src)]

if df.empty:
    empty_state("Khong co du lieu sau filter.")
    st.stop()


# ============================================================================
# 1. TIEN DO CHU KY + QUY HIEN TAI
# ============================================================================
st.markdown("### Tien do chu ky thi dua")

today = pd.Timestamp.now().normalize()
days_elapsed = max(0, min((today - COMP_START).days, (COMP_END - COMP_START).days))
days_remaining = max(0, (COMP_END - today).days)
pct_elapsed = days_elapsed / (COMP_END - COMP_START).days * 100
months_elapsed = min(12, max(0, (today.year - COMP_START.year) * 12 + today.month - COMP_START.month))
current_q = _get_current_quarter()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ngay da qua", f"{days_elapsed} / {(COMP_END - COMP_START).days}")
c2.metric("Ngay con lai", fmt_num(days_remaining))
c3.metric("Quy hien tai", current_q.split(" ")[0])
c4.metric("Tien do", f"{pct_elapsed:.1f}%")

st.progress(min(pct_elapsed / 100, 1.0))

st.divider()


# ============================================================================
# 2. DIEM THEO THANG & QUY
# ============================================================================
st.markdown("### Diem theo thang va quy")

# Compute monthly revenue per sale
monthly_rev = df.groupby([sale_col, "month"]).agg(
    revenue=("Doanh thu trước thuế", "sum"),
    n_hd=("Số hợp đồng", "nunique") if "Số hợp đồng" in df.columns else (sale_col, "count"),
    cap_thi_dua=("Cap thi dua", "first"),
    source=("Source", "first") if "Source" in df.columns else (sale_col, "first"),
).reset_index()

monthly_rev["month_rank"] = monthly_rev.groupby("month")["revenue"].rank(ascending=False, method="min")
monthly_rev["rank_bonus"] = monthly_rev["month_rank"].apply(_monthly_rank_bonus)
monthly_rev["diem_dt"] = monthly_rev["revenue"].apply(_compute_points)
monthly_rev["diem_thang"] = monthly_rev["diem_dt"] + monthly_rev["rank_bonus"]
monthly_rev["month_ts"] = monthly_rev["month"].dt.to_timestamp()

# Assign quarter label
def _month_to_quarter(m):
    ts = m.to_timestamp()
    for qn, (qs, qe) in QUARTERS.items():
        if qs <= ts <= qe:
            return qn
    return ""

monthly_rev["quarter"] = monthly_rev["month"].apply(_month_to_quarter)

# ── Quarterly tabs ──
closed_qs = [q for q in QUARTERS if _is_quarter_closed(q)]
open_qs = [q for q in QUARTERS if not _is_quarter_closed(q) and monthly_rev[monthly_rev["quarter"] == q].shape[0] > 0]

tab_labels = []
for q in QUARTERS:
    if _is_quarter_closed(q):
        tab_labels.append(f"{q} — DA CHOT")
    elif q == current_q:
        tab_labels.append(f"{q} — DANG DIEN RA")
    else:
        tab_labels.append(q)

# Only show tabs that have data or are current
active_tabs = []
for i, q in enumerate(QUARTERS):
    if _is_quarter_closed(q) or q == current_q:
        active_tabs.append((tab_labels[i], q))

if active_tabs:
    tabs = st.tabs([t[0] for t in active_tabs])

    for tab, (label, qname) in zip(tabs, active_tabs):
        with tab:
            qs, qe = QUARTERS[qname]
            q_data = monthly_rev[monthly_rev["quarter"] == qname]
            is_closed = _is_quarter_closed(qname)

            if q_data.empty:
                st.info(f"Chua co du lieu cho {qname}.")
                continue

            if is_closed:
                st.success(f"Quy nay da ket thuc ({qs.strftime('%d/%m')} - {qe.strftime('%d/%m/%Y')})")
            else:
                days_in_q = (qe - qs).days + 1
                days_done = min((today - qs).days, days_in_q)
                st.info(f"Dang dien ra — {days_done}/{days_in_q} ngay ({days_done/days_in_q*100:.0f}%)")

            # Monthly breakdown within quarter
            months_in_q = sorted(q_data["month"].unique())

            # Pivot: sale x month → points
            q_pivot = q_data.pivot_table(
                index=[sale_col, "cap_thi_dua", "source"],
                columns="month",
                values="diem_thang",
                aggfunc="sum",
                fill_value=0,
            ).reset_index()

            # Add quarter total
            month_cols = [c for c in q_pivot.columns if isinstance(c, pd.Period)]
            q_pivot["Tong diem quy"] = q_pivot[month_cols].sum(axis=1)
            q_pivot = q_pivot.sort_values("Tong diem quy", ascending=False).reset_index(drop=True)
            q_pivot.insert(0, "Hang", range(1, len(q_pivot) + 1))

            # Format column names
            disp_q = q_pivot.copy()
            rename_map = {sale_col: "Ho ten", "cap_thi_dua": "Cap", "source": "Source"}
            for m in month_cols:
                rename_map[m] = f"T{m.month:02d}/{m.year}"
            disp_q = disp_q.rename(columns=rename_map)

            st.dataframe(disp_q.head(30), hide_index=True, use_container_width=True)

            # Top 3 of quarter
            col_q1, col_q2, col_q3 = st.columns(3)
            top3_q = q_pivot.head(3)
            medals = ["1.", "2.", "3."]
            cols_q = [col_q1, col_q2, col_q3]
            for i, (_, row) in enumerate(top3_q.iterrows()):
                if i < 3:
                    with cols_q[i]:
                        st.metric(
                            f"{medals[i]} {row[sale_col]}",
                            f"{int(row['Tong diem quy'])} diem",
                        )

st.divider()


# ============================================================================
# 3. BANG XEP HANG TONG HOP (toan chu ky)
# ============================================================================
st.markdown("### Bang xep hang tong hop (toan chu ky)")

ranking = df.groupby([sale_col], as_index=False).agg(
    chuc_danh=("Chức danh", "first") if "Chức danh" in df.columns else (sale_col, "count"),
    cap_thi_dua=("Cap thi dua", "first"),
    source=("Source", "first") if "Source" in df.columns else (sale_col, "count"),
    channel=("Channel", "first") if "Channel" in df.columns else (sale_col, "count"),
    total_revenue=("Doanh thu trước thuế", "sum"),
    n_hd=("Số hợp đồng", "nunique") if "Số hợp đồng" in df.columns else (sale_col, "count"),
    n_months=(DATE_COL, lambda x: x.dt.to_period("M").nunique()),
)

ranking["Diem quy doi"] = ranking["total_revenue"].apply(_compute_points)

bonus_total = monthly_rev.groupby(sale_col)["rank_bonus"].sum().reset_index()
bonus_total.columns = [sale_col, "Bonus thang"]

top3_months = monthly_rev[monthly_rev["month_rank"] <= 3].groupby(sale_col).size().reset_index(name="Thang top 3")

ranking = ranking.merge(bonus_total, on=sale_col, how="left")
ranking = ranking.merge(top3_months, on=sale_col, how="left")
ranking["Bonus thang"] = ranking["Bonus thang"].fillna(0).astype(int)
ranking["Thang top 3"] = ranking["Thang top 3"].fillna(0).astype(int)
ranking["Tong diem"] = ranking["Diem quy doi"] + ranking["Bonus thang"]

ranking = ranking.sort_values("Tong diem", ascending=False).reset_index(drop=True)
ranking.insert(0, "Hang", range(1, len(ranking) + 1))

# Display columns
disp = ranking[[
    "Hang", sale_col, "cap_thi_dua", "source", "channel",
    "n_hd", "total_revenue", "Diem quy doi", "Bonus thang", "Tong diem",
    "Thang top 3", "n_months"
]].copy()
disp.columns = [
    "Hang", "Ho ten", "Cap", "Source", "Channel",
    "So HD", "Tong doanh thu", "Diem QD", "Bonus rank", "Tong diem",
    "Thang top 3", "Thang active"
]
disp["Tong doanh thu"] = disp["Tong doanh thu"].apply(lambda v: fmt_vnd(v, short=True))

tab_all, tab_gd, tab_tp, tab_cv = st.tabs(["Tat ca", "Giam Doc (Top 3)", "Truong Phong (Top 5)", "Chuyen Vien (Top 5)"])

with tab_all:
    st.dataframe(disp, hide_index=True, use_container_width=True, height=450)

with tab_gd:
    gd = disp[disp["Cap"] == "Giam Doc"].reset_index(drop=True)
    gd["Hang"] = range(1, len(gd) + 1)
    if not gd.empty:
        st.dataframe(gd.head(20), hide_index=True, use_container_width=True)
        st.success(f"Vung giai thuong: Top **3** — hien co **{min(3, len(gd))}** nguoi du dieu kien xet")
    else:
        empty_state("Khong co Giam Doc trong du lieu.")

with tab_tp:
    tp = disp[disp["Cap"] == "Truong Phong"].reset_index(drop=True)
    tp["Hang"] = range(1, len(tp) + 1)
    if not tp.empty:
        st.dataframe(tp.head(20), hide_index=True, use_container_width=True)
        st.success(f"Vung giai thuong: Top **5** — hien co **{min(5, len(tp))}** nguoi du dieu kien xet")
    else:
        empty_state("Khong co Truong Phong.")

with tab_cv:
    cv = disp[disp["Cap"] == "Chuyen Vien"].reset_index(drop=True)
    cv["Hang"] = range(1, len(cv) + 1)
    if not cv.empty:
        st.dataframe(cv.head(30), hide_index=True, use_container_width=True)
        st.success(f"Vung giai thuong: Top **5** — hien co **{min(5, len(cv))}** nguoi du dieu kien xet")
    else:
        empty_state("Khong co Chuyen Vien.")

st.divider()


# ============================================================================
# 4. TOP 10 BAR CHART + KHOANG CACH
# ============================================================================
st.markdown("### Top 10 — Tong diem + Khoang cach")
col_bar, col_gap = st.columns([3, 2])

with col_bar:
    top10 = ranking.head(10)
    if not top10.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top10[sale_col], x=top10["Diem quy doi"],
            name="Diem doanh thu", orientation="h",
            marker_color="#B44BC8",
            text=top10["Diem quy doi"], textposition="inside",
        ))
        fig.add_trace(go.Bar(
            y=top10[sale_col], x=top10["Bonus thang"],
            name="Bonus rank thang", orientation="h",
            marker_color="#E85BD8",
            text=top10["Bonus thang"], textposition="inside",
        ))
        fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed"))
        st.plotly_chart(apply_plotly_layout(fig, title="Top 10 tong diem (stacked)", height=400),
                        use_container_width=True)

with col_gap:
    st.markdown("**Khoang cach den vung giai thuong**")
    for cap, top_n in TOP_N.items():
        cap_df = ranking[ranking["cap_thi_dua"] == cap].head(top_n + 3)
        if len(cap_df) > top_n:
            threshold = cap_df.iloc[top_n - 1]["Tong diem"]
            first_out = cap_df.iloc[top_n]
            gap = threshold - first_out["Tong diem"]
            gap_revenue = gap * POINTS_PER
            st.markdown(
                f"**{cap}** (Top {top_n}):  \n"
                f"Nguong vao giai: **{int(threshold)} diem**  \n"
                f"Nguoi dau tien ngoai giai cach **{int(gap)} diem** "
                f"(~ {fmt_vnd(gap_revenue, short=True)} doanh thu)"
            )
        elif len(cap_df) > 0:
            st.markdown(f"**{cap}** (Top {top_n}): Chua du nguoi de so sanh")
        st.markdown("")

st.divider()


# ============================================================================
# 5. TIEN TRINH DIEM THEO THANG (line chart)
# ============================================================================
st.markdown("### Tien trinh tich luy diem theo thang")

top10_names = ranking.head(10)[sale_col].tolist()
if top10_names:
    monthly_top = monthly_rev[monthly_rev[sale_col].isin(top10_names)].copy()
    monthly_top = monthly_top.sort_values(["month_ts", sale_col])
    monthly_top["cum_points"] = monthly_top.groupby(sale_col)["diem_thang"].cumsum()

    fig = px.line(
        monthly_top, x="month_ts", y="cum_points", color=sale_col,
        markers=True,
        labels={"month_ts": "Thang", "cum_points": "Tong diem tich luy", sale_col: "Sale"},
    )
    fig.update_xaxes(dtick="M1", tickformat="%m/%Y")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(apply_plotly_layout(fig, title="", height=420), use_container_width=True)
else:
    empty_state()

st.divider()


# ============================================================================
# 6. HEATMAP RANK THANG
# ============================================================================
st.markdown("### Xep hang theo thang — Ai dan dau moi thang?")

n_show = st.slider("So sale hien thi", min_value=5, max_value=30, value=10, key="kpi_heatmap_n")

top_n_names = ranking.head(n_show)[sale_col].tolist()
if top_n_names:
    heat_data = monthly_rev[monthly_rev[sale_col].isin(top_n_names)].copy()
    heat_data["month_str"] = heat_data["month"].astype(str)
    heat_pivot = heat_data.pivot_table(
        index=sale_col, columns="month_str", values="month_rank", aggfunc="first"
    )
    heat_pivot = heat_pivot.loc[heat_pivot.mean(axis=1).sort_values().index]

    fig = px.imshow(
        heat_pivot.values,
        x=heat_pivot.columns.tolist(),
        y=heat_pivot.index.tolist(),
        aspect="auto",
        color_continuous_scale=["#5FBFA0", "#FDF2FB", "#E8738F"],
        text_auto=".0f",
        labels=dict(color="Hang"),
    )
    fig.update_layout(height=max(300, 35 * n_show))
    st.plotly_chart(apply_plotly_layout(fig, title="Hang moi thang (1 = dan dau, xanh = tot, hong = thap)"),
                    use_container_width=True)

st.divider()


# ============================================================================
# 7. SO SANH 1:1
# ============================================================================
st.markdown("### So sanh 1 vs 1")

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

        metrics = ["Tong diem", "Diem quy doi", "Bonus thang", "total_revenue", "n_hd", "Thang top 3"]
        labels  = ["Tong diem", "Diem QD", "Bonus rank", "Doanh thu", "So HD", "Thang top 3"]

        c1, c2, c3 = st.columns([2, 1, 2])
        with c1:
            st.markdown(f"**{sale_a}**")
            st.caption(f"Hang {int(row_a['Hang'])} | {row_a['cap_thi_dua']}")
        with c2:
            st.markdown("<div style='text-align:center'>vs</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"**{sale_b}**")
            st.caption(f"Hang {int(row_b['Hang'])} | {row_b['cap_thi_dua']}")

        values_a = [float(row_a[m]) for m in metrics]
        values_b = [float(row_b[m]) for m in metrics]
        max_vals = [max(a, b, 1) for a, b in zip(values_a, values_b)]
        norm_a = [a / m for a, m in zip(values_a, max_vals)]
        norm_b = [b / m for b, m in zip(values_b, max_vals)]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=norm_a + [norm_a[0]], theta=labels + [labels[0]],
            fill="toself", name=sale_a,
            fillcolor="rgba(180, 75, 200, 0.2)", line_color="#B44BC8",
        ))
        fig.add_trace(go.Scatterpolar(
            r=norm_b + [norm_b[0]], theta=labels + [labels[0]],
            fill="toself", name=sale_b,
            fillcolor="rgba(240, 110, 194, 0.2)", line_color="#F06EC2",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1.1])),
            height=380,
        )
        st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

        monthly_ab = monthly_rev[monthly_rev[sale_col].isin([sale_a, sale_b])].copy()
        if not monthly_ab.empty:
            fig2 = px.bar(
                monthly_ab, x="month_ts", y="diem_thang", color=sale_col,
                barmode="group",
                color_discrete_map={sale_a: "#B44BC8", sale_b: "#F06EC2"},
                labels={"month_ts": "Thang", "diem_thang": "Diem"},
            )
            fig2.update_xaxes(dtick="M1", tickformat="%m/%Y")
            st.plotly_chart(apply_plotly_layout(fig2, title="Diem theo thang", height=320),
                            use_container_width=True)
    elif sale_a == sale_b:
        st.info("Chon 2 sale khac nhau de so sanh.")

st.divider()


# ============================================================================
# 8. DU BAO
# ============================================================================
st.markdown("### Du bao cuoi chu ky (uoc tinh)")

if months_elapsed > 0 and not ranking.empty:
    ranking["Toc do diem/thang"] = (ranking["Tong diem"] / max(months_elapsed, 1)).round(1)
    ranking["Du bao cuoi ky"] = (ranking["Toc do diem/thang"] * 12).round(0).astype(int)

    forecast_df = ranking.head(15)[[sale_col, "cap_thi_dua", "Tong diem", "Toc do diem/thang", "Du bao cuoi ky"]].copy()
    forecast_df.columns = ["Ho ten", "Cap", "Diem hien tai", "Toc do/thang", "Du bao cuoi ky (12 thang)"]
    forecast_df.insert(0, "Hang", range(1, len(forecast_df) + 1))
    st.dataframe(forecast_df, hide_index=True, use_container_width=True)

    st.caption(
        "Du bao dua tren gia dinh toc do tich diem giu nguyen. "
        "Thuc te co the thay doi do chuong trinh moi, mua vu, thay doi nhan su."
    )
else:
    st.info("Can it nhat 1 thang du lieu trong chu ky thi dua.")

st.divider()


# ============================================================================
# FOOTER
# ============================================================================
st.markdown(
    "---\n"
    "*Du lieu cap nhat hang ngay. Ket qua chinh thuc do Ban To chuc cong bo thang 04/2027. "
    "Bang xep hang nay chi mang tinh chat tham khao.*"
)
