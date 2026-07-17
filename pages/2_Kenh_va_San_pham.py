"""
Trang 2 — Kênh & Sản phẩm
Charts: Sunburst / Bar theo Channel / Treemap Nhà BH / Grouped Bar top sản phẩm /
        Pie Loại BH / Stacked bar add-ons BHSK
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.data import (
    COLORS, DATE_COL,
    apply_filters, apply_plotly_layout, empty_state, fmt_vnd,
    load_master_data, render_sidebar_filters,
)

st.set_page_config(page_title="Kênh & Sản phẩm", layout="wide")

from lib.auth import require_auth
require_auth("kenh", "Kênh & Sản phẩm")

from lib.theme import inject_css
inject_css()


st.title("Kênh & Sản phẩm")
st.caption("Phân tích mix sản phẩm, kênh nào bán tốt, nhà bảo hiểm nào là chủ lực.")

df_raw = load_master_data()
if df_raw.empty:
    empty_state("Chưa có data.")
    st.stop()

filters = render_sidebar_filters(df_raw)
df = apply_filters(df_raw, filters)
if df.empty:
    empty_state()
    st.stop()

# ============================================================================
# 2.1 Sunburst: Source Channel Loại BH (top 5) Sản phẩm
# ============================================================================
st.markdown("### Phân cấp doanh thu: Source Channel Loại BH Sản phẩm")
st.caption("Click vào 1 phần để zoom vào. Click vào giữa để back.")

sb = df.copy()
# Top 5 sản phẩm mỗi (Source, Channel, Loại BH) — tránh ngoại vi rối rắm
top_products = (sb.groupby(["Source", "Channel", "Loại bảo hiểm", "Sản phẩm"], as_index=False)
                  ["Doanh thu trước thuế"].sum())
top_products["_rank"] = top_products.groupby(["Source", "Channel", "Loại bảo hiểm"])["Doanh thu trước thuế"] \
                                    .rank(method="dense", ascending=False)
sb_view = top_products[top_products["_rank"] <= 5].copy()
# Gộp "Khác" cho các sản phẩm ngoài top 5
others = top_products[top_products["_rank"] > 5].copy()
if not others.empty:
    others_g = others.groupby(["Source", "Channel", "Loại bảo hiểm"], as_index=False)["Doanh thu trước thuế"].sum()
    others_g["Sản phẩm"] = "Khác"
    others_g["_rank"] = 6
    sb_view = pd.concat([sb_view, others_g], ignore_index=True)

if not sb_view.empty:
    fig = px.sunburst(
        sb_view,
        path=["Source", "Channel", "Loại bảo hiểm", "Sản phẩm"],
        values="Doanh thu trước thuế",
        color="Source",
        color_discrete_map=COLORS,
    )
    fig.update_traces(hovertemplate="<b>%{label}</b><br>DT: %{value:,.0f} ₫<br>%{percentParent} of parent<extra></extra>")
    st.plotly_chart(apply_plotly_layout(fig, height=600), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 2.2 Bar horizontal — Doanh thu theo Channel
# 2.3 Pie — Loại BH
# ============================================================================
left, right = st.columns([2, 1])

with left:
    st.markdown("#### Doanh thu theo Channel")
    by_channel = (df.groupby(["Channel", "Source"], as_index=False)["Doanh thu trước thuế"]
                    .sum().sort_values("Doanh thu trước thuế", ascending=True))
    if not by_channel.empty:
        fig = px.bar(
            by_channel, x="Doanh thu trước thuế", y="Channel",
            color="Source", orientation="h",
            color_discrete_map=COLORS,
            text_auto=".2s",
        )
        fig.update_xaxes(title="Doanh thu (VNĐ)", tickformat=",")
        fig.update_yaxes(title="")
        st.plotly_chart(apply_plotly_layout(fig, height=440), use_container_width=True)
    else:
        empty_state()

with right:
    st.markdown("#### Cơ cấu Loại bảo hiểm")
    by_loai = df.groupby("Loại bảo hiểm", as_index=False)["Doanh thu trước thuế"].sum() \
                .sort_values("Doanh thu trước thuế", ascending=False)
    if not by_loai.empty:
        fig = px.pie(
            by_loai, names="Loại bảo hiểm", values="Doanh thu trước thuế",
            color="Loại bảo hiểm", color_discrete_map=COLORS, hole=0.35,
        )
        fig.update_traces(hovertemplate="<b>%{label}</b><br>%{value:,.0f} ₫<br>%{percent}<extra></extra>")
        st.plotly_chart(apply_plotly_layout(fig, height=440), use_container_width=True)
    else:
        empty_state()

st.divider()

# ============================================================================
# 2.4 Nha BH x Loai BH — Grouped horizontal bar (thay treemap)
# ============================================================================
st.markdown("### Nha bao hiem — Doanh thu theo Loai BH")
st.caption("Moi nhom = 1 nha BH, chia mau theo loai bao hiem. So sanh truc quan.")

tm = df.groupby(["Nhà BH", "Loại bảo hiểm"], as_index=False).agg(
    DT=("Doanh thu trước thuế", "sum"),
)
tm = tm[tm["DT"] > 0]
if not tm.empty:
    # Top 12 nha BH theo tong DT
    top_nha = tm.groupby("Nhà BH")["DT"].sum().nlargest(12).index.tolist()
    tm_top = tm[tm["Nhà BH"].isin(top_nha)]

    fig = px.bar(
        tm_top,
        x="DT", y="Nhà BH", color="Loại bảo hiểm",
        orientation="h",
        color_discrete_map=COLORS,
        text_auto=".2s",
        labels={"DT": "Doanh thu (VND)", "Nhà BH": ""},
    )
    fig.update_layout(
        barmode="stack",
        yaxis=dict(categoryorder="total ascending"),
        legend=dict(title="Loai BH"),
    )
    fig.update_xaxes(tickformat=",")
    st.plotly_chart(apply_plotly_layout(fig, height=max(400, 40 * len(top_nha))),
                    use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 2.5 Grouped Bar: Top 15 sản phẩm × Source
# ============================================================================
st.markdown("### Top 15 sản phẩm — chia theo Source")
top15 = (df.groupby("Sản phẩm", as_index=False)["Doanh thu trước thuế"]
           .sum().nlargest(15, "Doanh thu trước thuế")["Sản phẩm"].tolist())
gb = df[df["Sản phẩm"].isin(top15)].groupby(["Sản phẩm", "Source"], as_index=False)["Doanh thu trước thuế"].sum()
if not gb.empty:
    # Sort products by total DT desc
    order = (gb.groupby("Sản phẩm")["Doanh thu trước thuế"].sum()
                .sort_values(ascending=False).index.tolist())
    fig = px.bar(
        gb, x="Sản phẩm", y="Doanh thu trước thuế", color="Source",
        barmode="group", color_discrete_map=COLORS,
        category_orders={"Sản phẩm": order},
    )
    fig.update_xaxes(tickangle=-40)
    fig.update_yaxes(title="Doanh thu (VNĐ)", tickformat=",")
    st.plotly_chart(apply_plotly_layout(fig, height=500), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 2.6 BHSK Add-ons: Ngoại trú / Nha khoa / Thai sản / Topup
# ============================================================================
st.markdown("### BHSK Add-ons")
st.caption("Chỉ áp dụng cho HĐ Loại BH = BHSK. Có / Không có từng gói bổ trợ.")

df_bhsk = df[df["Loại bảo hiểm"] == "BHSK"].copy()
if not df_bhsk.empty:
    addon_cols = ["Ngoại trú", "Nha khoa", "Thai sản", "Topup"]
    a1, a2, a3, a4 = st.columns(4)
    for col_name, place in zip(addon_cols, [a1, a2, a3, a4]):
        if col_name not in df_bhsk.columns:
            place.info(f"Không có cột {col_name}")
            continue
        s = df_bhsk[col_name].fillna("").astype(str).str.strip()
        has = s.apply(lambda x: "Có" if x not in ("", "nan", "None", "0") else "Không")
        agg = (pd.DataFrame({"has": has, "dt": df_bhsk["Doanh thu trước thuế"].values})
                 .groupby("has", as_index=False)["dt"].sum())
        if agg.empty:
            place.info(f"{col_name}: trống")
            continue
        fig = px.pie(agg, names="has", values="dt", hole=0.5,
                     color="has",
                     color_discrete_map={"Có": "#2ECC71", "Không": "#BDC3C7"})
        fig.update_traces(textinfo="label+percent",
                          hovertemplate="<b>%{label}</b><br>%{value:,.0f} ₫<extra></extra>")
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0),
                          title=dict(text=col_name, x=0.5, xanchor="center"),
                          height=250)
        place.plotly_chart(fig, use_container_width=True)
else:
    st.info("Không có HĐ BHSK trong bộ lọc hiện tại.")
