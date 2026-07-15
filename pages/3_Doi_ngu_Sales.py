"""
Trang 3 — Đội ngũ Sales
Charts: Top 20 salesperson / BDM cards / BDD cards / Sankey CTV→BDM→BDD /
        Scatter HĐ vs Doanh thu / Detail table
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.data import (
    COLORS, DATE_COL,
    apply_filters, apply_plotly_layout, empty_state, fmt_num, fmt_vnd,
    load_master_data, render_sidebar_filters,
)

st.set_page_config(page_title="Đội ngũ Sales", page_icon=None, layout="wide")
st.title("Đội ngũ Sales")
st.caption("Ranking sale, hiệu suất BDM/BDD, phát hiện star performer.")

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
# 3.1 Top 20 salesperson
# ============================================================================
st.markdown("### Top 20 Salesperson theo Doanh thu")

if "Họ tên sale" in df.columns:
    top_sales = (df.groupby(["Họ tên sale", "Chức danh"], as_index=False)
                   .agg(Doanh_thu=("Doanh thu trước thuế", "sum"),
                        So_HD=("Số hợp đồng", "nunique"),
                        EST_Bonus=("EST_Bonus", "sum"))
                   .sort_values("Doanh_thu", ascending=False)
                   .head(20))
    if not top_sales.empty:
        fig = px.bar(
            top_sales.sort_values("Doanh_thu", ascending=True),
            x="Doanh_thu", y="Họ tên sale", color="Chức danh",
            orientation="h",
            hover_data={"So_HD": ":,", "EST_Bonus": ":,"},
            text_auto=".2s",
        )
        fig.update_xaxes(title="Doanh thu (VNĐ)", tickformat=",")
        fig.update_yaxes(title="")
        st.plotly_chart(apply_plotly_layout(fig, height=650), use_container_width=True)
    else:
        empty_state()
else:
    st.warning("Không có cột `Họ tên sale`")

st.divider()

# ============================================================================
# 3.2 BDM Performance cards
# ============================================================================
st.markdown("### Hiệu suất BDM (Quản lý cấp 1)")

if "QUẢN LÝ CẤP 1 (BDM)" in df.columns:
    df_bdm = df[df["QUẢN LÝ CẤP 1 (BDM)"].notna() & (df["QUẢN LÝ CẤP 1 (BDM)"] != "")]
    bdm_perf = (df_bdm.groupby("QUẢN LÝ CẤP 1 (BDM)", as_index=False)
                       .agg(Doanh_thu=("Doanh thu trước thuế", "sum"),
                            So_sale=("Họ tên sale", "nunique"),
                            So_HD=("Số hợp đồng", "nunique"),
                            Affina_Rev=("Affina_Revenue", "sum"))
                       .sort_values("Doanh_thu", ascending=False))
    if not bdm_perf.empty:
        # Show as bar chart + table
        fig = px.bar(
            bdm_perf.head(15), x="QUẢN LÝ CẤP 1 (BDM)", y="Doanh_thu",
            color="Doanh_thu", color_continuous_scale="Blues",
            hover_data={"So_sale": True, "So_HD": ":,"},
        )
        fig.update_xaxes(tickangle=-40, title="")
        fig.update_yaxes(title="Doanh thu (VNĐ)", tickformat=",")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(apply_plotly_layout(fig, height=400), use_container_width=True)

        st.dataframe(
            bdm_perf,
            column_config={
                "QUẢN LÝ CẤP 1 (BDM)": "BDM",
                "Doanh_thu": st.column_config.NumberColumn("Doanh thu", format="%.0f ₫"),
                "So_sale": st.column_config.NumberColumn("Số sale", format="%d"),
                "So_HD": st.column_config.NumberColumn("Số HĐ", format="%d"),
                "Affina_Rev": st.column_config.NumberColumn("Affina Rev", format="%.0f ₫"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        empty_state("Không có data BDM")
else:
    st.info("Không có cột BDM")

st.divider()

# ============================================================================
# 3.3 BDD Performance
# ============================================================================
st.markdown("### Hiệu suất BDD (Quản lý cấp 2)")

if "QUẢN LÝ CẤP 2 (BDD)" in df.columns:
    df_bdd = df[df["QUẢN LÝ CẤP 2 (BDD)"].notna() & (df["QUẢN LÝ CẤP 2 (BDD)"] != "")]
    bdd_perf = (df_bdd.groupby("QUẢN LÝ CẤP 2 (BDD)", as_index=False)
                       .agg(Doanh_thu=("Doanh thu trước thuế", "sum"),
                            So_BDM=("QUẢN LÝ CẤP 1 (BDM)", "nunique"),
                            So_sale=("Họ tên sale", "nunique"),
                            So_HD=("Số hợp đồng", "nunique"))
                       .sort_values("Doanh_thu", ascending=False))
    if not bdd_perf.empty:
        fig = px.bar(
            bdd_perf.head(10), x="QUẢN LÝ CẤP 2 (BDD)", y="Doanh_thu",
            color="Doanh_thu", color_continuous_scale="Purples",
        )
        fig.update_xaxes(tickangle=-40, title="")
        fig.update_yaxes(title="Doanh thu (VNĐ)", tickformat=",")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(apply_plotly_layout(fig, height=400), use_container_width=True)

        st.dataframe(
            bdd_perf,
            column_config={
                "QUẢN LÝ CẤP 2 (BDD)": "BDD",
                "Doanh_thu": st.column_config.NumberColumn("Doanh thu", format="%.0f ₫"),
                "So_BDM": st.column_config.NumberColumn("Số BDM", format="%d"),
                "So_sale": st.column_config.NumberColumn("Số sale", format="%d"),
                "So_HD": st.column_config.NumberColumn("Số HĐ", format="%d"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        empty_state("Không có data BDD")
else:
    st.info("Không có cột BDD")

st.divider()

# ============================================================================
# 3.4 Sankey: Sale → BDM → BDD
# ============================================================================
st.markdown("### Sankey: CTV → BDM → BDD (top 30 dòng chảy)")
st.caption("Chiều rộng luồng ∝ doanh thu. Hover để xem chi tiết.")

sk = df[df["QUẢN LÝ CẤP 1 (BDM)"].notna() & df["QUẢN LÝ CẤP 2 (BDD)"].notna() & df["Họ tên sale"].notna()].copy()

if not sk.empty:
    # Aggregate: từ Sale → BDM
    flow_sale_bdm = (sk.groupby(["Họ tên sale", "QUẢN LÝ CẤP 1 (BDM)"], as_index=False)
                       ["Doanh thu trước thuế"].sum())
    flow_sale_bdm = flow_sale_bdm.nlargest(30, "Doanh thu trước thuế")

    # BDM → BDD
    flow_bdm_bdd = (sk.groupby(["QUẢN LÝ CẤP 1 (BDM)", "QUẢN LÝ CẤP 2 (BDD)"], as_index=False)
                      ["Doanh thu trước thuế"].sum())

    # Node list
    nodes = list(pd.unique(pd.concat([
        flow_sale_bdm["Họ tên sale"],
        flow_sale_bdm["QUẢN LÝ CẤP 1 (BDM)"],
        flow_bdm_bdd["QUẢN LÝ CẤP 1 (BDM)"],
        flow_bdm_bdd["QUẢN LÝ CẤP 2 (BDD)"],
    ])))
    node_idx = {n: i for i, n in enumerate(nodes)}

    source_i, target_i, value_i = [], [], []
    for _, r in flow_sale_bdm.iterrows():
        source_i.append(node_idx[r["Họ tên sale"]])
        target_i.append(node_idx[r["QUẢN LÝ CẤP 1 (BDM)"]])
        value_i.append(r["Doanh thu trước thuế"])
    for _, r in flow_bdm_bdd.iterrows():
        if r["QUẢN LÝ CẤP 1 (BDM)"] not in flow_sale_bdm["QUẢN LÝ CẤP 1 (BDM)"].values:
            continue
        source_i.append(node_idx[r["QUẢN LÝ CẤP 1 (BDM)"]])
        target_i.append(node_idx[r["QUẢN LÝ CẤP 2 (BDD)"]])
        value_i.append(r["Doanh thu trước thuế"])

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15, thickness=18,
            line=dict(color="black", width=0.5),
            label=nodes,
        ),
        link=dict(source=source_i, target=target_i, value=value_i,
                  hovertemplate="Từ %{source.label} → %{target.label}<br>DT: %{value:,.0f} ₫<extra></extra>"),
    )])
    fig.update_layout(font=dict(size=11), height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    empty_state("Chưa có luồng CTV→BDM→BDD hợp lệ trong bộ lọc.")

st.divider()

# ============================================================================
# 3.5 Scatter — HĐ vs Doanh thu (mỗi điểm = 1 sale)
# ============================================================================
st.markdown("### Scatter: Số HĐ × Doanh thu / Sale")
st.caption("Góc phải-trên = star performer. Kích thước bubble = Affina Revenue.")

scatter_df = (df.groupby(["Họ tên sale", "Chức danh"], as_index=False)
                .agg(So_HD=("Số hợp đồng", "nunique"),
                     Doanh_thu=("Doanh thu trước thuế", "sum"),
                     Affina=("Affina_Revenue", "sum"),
                     BDM=("QUẢN LÝ CẤP 1 (BDM)", "first"),
                     BDD=("QUẢN LÝ CẤP 2 (BDD)", "first")))
scatter_df = scatter_df[scatter_df["Doanh_thu"] > 0]

if not scatter_df.empty:
    fig = px.scatter(
        scatter_df, x="So_HD", y="Doanh_thu",
        size="Affina", color="Chức danh",
        hover_data={"Họ tên sale": True, "BDM": True, "BDD": True,
                    "So_HD": ":,", "Doanh_thu": ":,", "Affina": ":,"},
        size_max=40, opacity=0.75,
    )
    fig.update_xaxes(title="Số HĐ", tickformat=",")
    fig.update_yaxes(title="Doanh thu (VNĐ)", tickformat=",")
    st.plotly_chart(apply_plotly_layout(fig, height=550), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 3.6 Full detail table (with search + download)
# ============================================================================
st.markdown("### Bảng chi tiết toàn bộ Sales")

detail = (df.groupby(["Họ tên sale", "Chức danh",
                      "QUẢN LÝ CẤP 1 (BDM)", "QUẢN LÝ CẤP 2 (BDD)"], as_index=False, dropna=False)
            .agg(So_HD=("Số hợp đồng", "nunique"),
                 Doanh_thu=("Doanh thu trước thuế", "sum"),
                 EST_Bonus=("EST_Bonus", "sum"),
                 Affina=("Affina_Revenue", "sum"))
            .sort_values("Doanh_thu", ascending=False))
detail.insert(0, "#", range(1, len(detail) + 1))

st.dataframe(
    detail,
    column_config={
        "QUẢN LÝ CẤP 1 (BDM)": "BDM",
        "QUẢN LÝ CẤP 2 (BDD)": "BDD",
        "Doanh_thu": st.column_config.NumberColumn("Doanh thu", format="%.0f ₫"),
        "EST_Bonus": st.column_config.NumberColumn("EST Bonus", format="%.0f ₫"),
        "Affina": st.column_config.NumberColumn("Affina Rev", format="%.0f ₫"),
        "So_HD": st.column_config.NumberColumn("Số HĐ", format="%d"),
    },
    hide_index=True,
    use_container_width=True,
    height=500,
)

csv = detail.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="Tải xuống CSV",
    data=csv,
    file_name="affina_sales_ranking.csv",
    mime="text/csv",
)
