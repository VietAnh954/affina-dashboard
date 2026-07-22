"""
================================================================================
 TRANG 12 — MY DASHBOARD (Phase 4)
================================================================================
Trang ca nhan cho tung sale xem KPI cua minh.
Admin/Head: chon bat ky sale nao.
Sale: chi thay data cua minh (match theo display_name).
================================================================================
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.auth import require_auth, render_user_info, get_current_user, get_role
from lib.data import (
    COLORS, DATE_COL,
    apply_plotly_layout, empty_state,
    fmt_num, fmt_vnd,
    load_master_data,
)

st.set_page_config(page_title="My Dashboard", layout="wide")

require_auth("home", "My Dashboard")
render_user_info()

from lib.theme import inject_css, render_header
inject_css()
render_header()

st.title("My Dashboard")
st.caption("Hieu suat ca nhan — doanh thu, so HD, xu huong hang thang.")

# ── Load data ──
df_all = load_master_data()
if df_all.empty:
    st.warning("Chua co du lieu.")
    st.stop()

df_all[DATE_COL] = pd.to_datetime(df_all[DATE_COL], errors="coerce")

sale_col = "Họ tên sale" if "Họ tên sale" in df_all.columns else "Họ tên"
if sale_col not in df_all.columns:
    st.error("Khong tim thay cot ten sale.")
    st.stop()

all_sales = sorted(df_all[sale_col].dropna().unique().tolist())

# ── Determine which sale to show ──
user = get_current_user()
role = get_role()

if role in ("admin", "head"):
    selected_sale = st.selectbox(
        "Chon sale",
        options=all_sales,
        index=0,
        key="my_dash_sale",
    )
else:
    display_name = user.get("display_name", "") if user else ""
    matched = [s for s in all_sales if s.lower() == display_name.lower()]
    if matched:
        selected_sale = matched[0]
    else:
        close_matches = [s for s in all_sales if display_name.lower() in s.lower()]
        if close_matches:
            selected_sale = close_matches[0]
        else:
            st.warning(
                f"Khong tim thay du lieu cho \"{display_name}\". "
                f"Lien he admin de cap nhat display_name trong tai khoan."
            )
            st.stop()
    st.info(f"Dang xem: **{selected_sale}**")

# ── Filter data for selected sale ──
df = df_all[df_all[sale_col] == selected_sale].copy()

if df.empty:
    empty_state(f"Chua co du lieu cho {selected_sale}.")
    st.stop()

# ============================================================================
# 1. KPI TONG QUAN
# ============================================================================
st.markdown("### Tong quan")

total_rev = df["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df.columns else 0
total_hd = df["Số hợp đồng"].nunique() if "Số hợp đồng" in df.columns else len(df)
n_months = df[DATE_COL].dt.to_period("M").nunique()
avg_rev_month = total_rev / max(n_months, 1)

chuc_danh = df["Chức danh"].iloc[0] if "Chức danh" in df.columns and not df["Chức danh"].isna().all() else "N/A"
source = df["Source"].iloc[0] if "Source" in df.columns and not df["Source"].isna().all() else "N/A"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Tong doanh thu", fmt_vnd(total_rev, short=True))
c2.metric("So hop dong", fmt_num(total_hd))
c3.metric("TB thang", fmt_vnd(avg_rev_month, short=True))
c4.metric("Chuc danh", str(chuc_danh))
c5.metric("Source", str(source))

st.divider()

# ============================================================================
# 2. DOANH THU THEO THANG
# ============================================================================
st.markdown("### Doanh thu theo thang")

df["month"] = df[DATE_COL].dt.to_period("M")
monthly = df.groupby("month").agg(
    revenue=("Doanh thu trước thuế", "sum") if "Doanh thu trước thuế" in df.columns else (sale_col, "count"),
    n_hd=("Số hợp đồng", "nunique") if "Số hợp đồng" in df.columns else (sale_col, "count"),
).reset_index()
monthly["month_ts"] = monthly["month"].dt.to_timestamp()

fig = go.Figure()
fig.add_trace(go.Bar(
    x=monthly["month_ts"], y=monthly["revenue"],
    name="Doanh thu",
    marker_color="#B44BC8",
    text=monthly["revenue"].apply(lambda v: fmt_vnd(v, short=True)),
    textposition="outside",
))
fig.update_xaxes(dtick="M1", tickformat="%m/%Y")
fig.update_layout(yaxis_title="Doanh thu (VND)")
st.plotly_chart(
    apply_plotly_layout(fig, title="", height=380),
    use_container_width=True,
)

st.divider()

# ============================================================================
# 3. SO SANH VOI TRUNG BINH TEAM
# ============================================================================
st.markdown("### So sanh voi trung binh team")

team_monthly = df_all.groupby([df_all[DATE_COL].dt.to_period("M")]).agg(
    total_rev=("Doanh thu trước thuế", "sum") if "Doanh thu trước thuế" in df_all.columns else (sale_col, "count"),
    n_sales=(sale_col, "nunique"),
).reset_index()
team_monthly.columns = ["month", "total_rev", "n_sales"]
team_monthly["avg_rev"] = team_monthly["total_rev"] / team_monthly["n_sales"].clip(lower=1)
team_monthly["month_ts"] = team_monthly["month"].dt.to_timestamp()

merged = monthly.merge(
    team_monthly[["month", "avg_rev"]],
    on="month",
    how="left",
)

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=merged["month_ts"], y=merged["revenue"],
    name=selected_sale,
    marker_color="#B44BC8",
))
fig2.add_trace(go.Scatter(
    x=merged["month_ts"], y=merged["avg_rev"],
    name="TB team",
    mode="lines+markers",
    line=dict(color="#7D5BA6", width=2, dash="dot"),
    marker=dict(size=6),
))
fig2.update_xaxes(dtick="M1", tickformat="%m/%Y")
fig2.update_layout(barmode="overlay", yaxis_title="VND")
st.plotly_chart(
    apply_plotly_layout(fig2, title="", height=380),
    use_container_width=True,
)

st.divider()

# ============================================================================
# 4. TOP SAN PHAM
# ============================================================================
st.markdown("### San pham ban nhieu nhat")

if "Sản phẩm" in df.columns:
    product_rev = df.groupby("Sản phẩm").agg(
        revenue=("Doanh thu trước thuế", "sum") if "Doanh thu trước thuế" in df.columns else (sale_col, "count"),
        n_hd=("Số hợp đồng", "nunique") if "Số hợp đồng" in df.columns else (sale_col, "count"),
    ).reset_index().sort_values("revenue", ascending=False).head(10)

    fig3 = px.bar(
        product_rev, x="revenue", y="Sản phẩm",
        orientation="h",
        color_discrete_sequence=["#E85BD8"],
        labels={"revenue": "Doanh thu", "Sản phẩm": "San pham"},
    )
    fig3.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(
        apply_plotly_layout(fig3, title="", height=350),
        use_container_width=True,
    )
else:
    st.info("Khong co cot San pham trong data.")

st.divider()

# ============================================================================
# 5. XEP HANG TRONG TEAM
# ============================================================================
st.markdown("### Xep hang trong team")

if "Doanh thu trước thuế" in df_all.columns:
    ranking = df_all.groupby(sale_col)["Doanh thu trước thuế"].sum().reset_index()
    ranking.columns = [sale_col, "total_revenue"]
    ranking = ranking.sort_values("total_revenue", ascending=False).reset_index(drop=True)
    ranking["rank"] = range(1, len(ranking) + 1)

    my_rank = ranking[ranking[sale_col] == selected_sale]
    if not my_rank.empty:
        rank_val = int(my_rank.iloc[0]["rank"])
        total_sales = len(ranking)
        percentile = (1 - rank_val / total_sales) * 100

        r1, r2, r3 = st.columns(3)
        r1.metric("Xep hang", f"#{rank_val} / {total_sales}")
        r2.metric("Top %", f"{percentile:.0f}%")
        r3.metric("Tong DT", fmt_vnd(float(my_rank.iloc[0]["total_revenue"]), short=True))

st.divider()

# ============================================================================
# 6. CHI TIET GIAO DICH GAN DAY
# ============================================================================
st.markdown("### Giao dich gan day")

recent = df.sort_values(DATE_COL, ascending=False).head(20)
display_cols = [DATE_COL]
for c in ["Số hợp đồng", "Sản phẩm", "Đối tác nhà bảo hiểm", "Doanh thu trước thuế", "Source"]:
    if c in recent.columns:
        display_cols.append(c)
st.dataframe(recent[display_cols], hide_index=True, use_container_width=True)

# ============================================================================
# FOOTER
# ============================================================================
st.markdown(
    "---\n"
    "*Du lieu cap nhat hang ngay. Lien he admin neu thong tin khong chinh xac.*"
)
