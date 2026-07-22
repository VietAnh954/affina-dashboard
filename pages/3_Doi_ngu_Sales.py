"""
Trang 3 — Doi ngu Sales
Charts: Top 20 / BDM performance / BDD performance /
        Hierarchy grouped bar (thay Sankey) / Scatter / Detail table
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

st.set_page_config(page_title="Doi ngu Sales", layout="wide")

from lib.auth import require_auth, render_user_info
require_auth("sales", "Doi ngu Sales")
render_user_info()

from lib.theme import inject_css, render_header
inject_css()
render_header()

st.title("Doi ngu Sales")
st.caption("Ranking sale, hieu suat BDM/BDD, phat hien star performer.")

df_raw = load_master_data()
if df_raw.empty:
    empty_state("Chua co data.")
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
        fig.update_xaxes(title="Doanh thu (VND)", tickformat=",")
        fig.update_yaxes(title="")
        st.plotly_chart(apply_plotly_layout(fig, height=650), use_container_width=True)
    else:
        empty_state()
else:
    st.warning("Khong co cot `Ho ten sale`")

st.divider()

# ============================================================================
# 3.2 BDM Performance
# ============================================================================
st.markdown("### Hieu suat BDM (Quan ly cap 1)")

if "QUẢN LÝ CẤP 1 (BDM)" in df.columns:
    df_bdm = df[df["QUẢN LÝ CẤP 1 (BDM)"].notna() & (df["QUẢN LÝ CẤP 1 (BDM)"] != "")]
    bdm_perf = (df_bdm.groupby("QUẢN LÝ CẤP 1 (BDM)", as_index=False)
                       .agg(Doanh_thu=("Doanh thu trước thuế", "sum"),
                            So_sale=("Họ tên sale", "nunique"),
                            So_HD=("Số hợp đồng", "nunique"),
                            Affina_Rev=("Affina_Revenue", "sum"))
                       .sort_values("Doanh_thu", ascending=False))
    if not bdm_perf.empty:
        fig = px.bar(
            bdm_perf.head(15), x="QUẢN LÝ CẤP 1 (BDM)", y="Doanh_thu",
            color="Doanh_thu",
            color_continuous_scale=["#FDF2FB", "#F0AEE2", "#D06DC4", "#A6409E", "#7D2E78"],
            hover_data={"So_sale": True, "So_HD": ":,"},
        )
        fig.update_xaxes(tickangle=-40, title="")
        fig.update_yaxes(title="Doanh thu (VND)", tickformat=",")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(apply_plotly_layout(fig, height=400), use_container_width=True)

        st.dataframe(
            bdm_perf,
            column_config={
                "QUẢN LÝ CẤP 1 (BDM)": "BDM",
                "Doanh_thu": st.column_config.NumberColumn("Doanh thu", format="%.0f"),
                "So_sale": st.column_config.NumberColumn("So sale", format="%d"),
                "So_HD": st.column_config.NumberColumn("So HD", format="%d"),
                "Affina_Rev": st.column_config.NumberColumn("Affina Rev", format="%.0f"),
            },
            hide_index=True, use_container_width=True,
        )
    else:
        empty_state("Khong co data BDM")
else:
    st.info("Khong co cot BDM")

st.divider()

# ============================================================================
# 3.3 BDD Performance
# ============================================================================
st.markdown("### Hieu suat BDD (Quan ly cap 2)")

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
            color="Doanh_thu",
            color_continuous_scale=["#FDF2FB", "#E8C1F0", "#C77BC9", "#9B4FAE", "#6B3A8E"],
        )
        fig.update_xaxes(tickangle=-40, title="")
        fig.update_yaxes(title="Doanh thu (VND)", tickformat=",")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(apply_plotly_layout(fig, height=400), use_container_width=True)

        st.dataframe(
            bdd_perf,
            column_config={
                "QUẢN LÝ CẤP 2 (BDD)": "BDD",
                "Doanh_thu": st.column_config.NumberColumn("Doanh thu", format="%.0f"),
                "So_BDM": st.column_config.NumberColumn("So BDM", format="%d"),
                "So_sale": st.column_config.NumberColumn("So sale", format="%d"),
                "So_HD": st.column_config.NumberColumn("So HD", format="%d"),
            },
            hide_index=True, use_container_width=True,
        )
    else:
        empty_state("Khong co data BDD")
else:
    st.info("Khong co cot BDD")

st.divider()

# ============================================================================
# 3.4 THAY SANKEY => Grouped bar: BDD > BDM > top sale (hierarchy)
# ============================================================================
st.markdown("### Cau truc nhanh: BDD — BDM — So sale & Doanh thu")
st.caption("Moi bar = 1 BDM, nhom theo BDD. So sanh quy mo nhanh giua cac BDD.")

has_bdd = "QUẢN LÝ CẤP 2 (BDD)" in df.columns
has_bdm = "QUẢN LÝ CẤP 1 (BDM)" in df.columns

if has_bdd and has_bdm:
    hier = (df[df["QUẢN LÝ CẤP 2 (BDD)"].notna() & df["QUẢN LÝ CẤP 1 (BDM)"].notna()]
              .groupby(["QUẢN LÝ CẤP 2 (BDD)", "QUẢN LÝ CẤP 1 (BDM)"], as_index=False)
              .agg(doanh_thu=("Doanh thu trước thuế", "sum"),
                   so_sale=("Họ tên sale", "nunique"),
                   so_hd=("Số hợp đồng", "nunique")))
    hier = hier[hier["doanh_thu"] > 0]

    if not hier.empty:
        # Tab: bar doanh thu vs bar số sale
        tab_rev, tab_sale = st.tabs(["Doanh thu theo nhanh", "So sale theo nhanh"])

        with tab_rev:
            fig = px.bar(
                hier.sort_values("doanh_thu", ascending=True),
                x="doanh_thu",
                y="QUẢN LÝ CẤP 1 (BDM)",
                color="QUẢN LÝ CẤP 2 (BDD)",
                orientation="h",
                text_auto=".2s",
                hover_data={"so_sale": True, "so_hd": True},
                labels={"doanh_thu": "Doanh thu (VND)", "QUẢN LÝ CẤP 1 (BDM)": "BDM"},
            )
            fig.update_layout(
                barmode="group",
                yaxis=dict(categoryorder="total ascending"),
                legend=dict(title="BDD"),
            )
            fig.update_xaxes(tickformat=",")
            st.plotly_chart(apply_plotly_layout(fig, height=max(400, 30 * len(hier))),
                            use_container_width=True)

        with tab_sale:
            fig2 = px.bar(
                hier.sort_values("so_sale", ascending=True),
                x="so_sale",
                y="QUẢN LÝ CẤP 1 (BDM)",
                color="QUẢN LÝ CẤP 2 (BDD)",
                orientation="h",
                text_auto=True,
                labels={"so_sale": "So sale active", "QUẢN LÝ CẤP 1 (BDM)": "BDM"},
            )
            fig2.update_layout(
                barmode="group",
                yaxis=dict(categoryorder="total ascending"),
                legend=dict(title="BDD"),
            )
            st.plotly_chart(apply_plotly_layout(fig2, height=max(400, 30 * len(hier))),
                            use_container_width=True)

        # Summary table nhanh
        bdd_summary = (hier.groupby("QUẢN LÝ CẤP 2 (BDD)")
                           .agg(n_bdm=("QUẢN LÝ CẤP 1 (BDM)", "nunique"),
                                total_sale=("so_sale", "sum"),
                                total_dt=("doanh_thu", "sum"))
                           .sort_values("total_dt", ascending=False)
                           .reset_index())
        bdd_summary["DT/Sale"] = (bdd_summary["total_dt"] / bdd_summary["total_sale"].clip(lower=1)).round(0)
        bdd_summary.columns = ["BDD", "So BDM", "So Sale", "Tong DT", "DT trung binh / Sale"]
        bdd_summary["Tong DT"] = bdd_summary["Tong DT"].apply(lambda v: fmt_vnd(v, short=True))
        bdd_summary["DT trung binh / Sale"] = bdd_summary["DT trung binh / Sale"].apply(lambda v: fmt_vnd(v, short=True))
        st.dataframe(bdd_summary, hide_index=True, use_container_width=True)
    else:
        empty_state("Khong co du lieu hierarchy BDD-BDM.")
else:
    st.info("Can ca 2 cot BDM va BDD de ve bieu do nay.")

st.divider()

# ============================================================================
# 3.5 Scatter — HD vs Doanh thu
# ============================================================================
st.markdown("### Scatter: So HD x Doanh thu / Sale")
st.caption("Goc phai-tren = star performer. Kich thuoc = Affina Revenue.")

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
    fig.update_xaxes(title="So HD", tickformat=",")
    fig.update_yaxes(title="Doanh thu (VND)", tickformat=",")
    st.plotly_chart(apply_plotly_layout(fig, height=550), use_container_width=True)
else:
    empty_state()

st.divider()

# ============================================================================
# 3.6 Detail table
# ============================================================================
st.markdown("### Bang chi tiet toan bo Sales")

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
        "Doanh_thu": st.column_config.NumberColumn("Doanh thu", format="%.0f"),
        "EST_Bonus": st.column_config.NumberColumn("EST Bonus", format="%.0f"),
        "Affina": st.column_config.NumberColumn("Affina Rev", format="%.0f"),
        "So_HD": st.column_config.NumberColumn("So HD", format="%d"),
    },
    hide_index=True, use_container_width=True, height=500,
)

csv = detail.to_csv(index=False).encode("utf-8-sig")
st.download_button("Tai xuong CSV", data=csv, file_name="affina_sales_ranking.csv", mime="text/csv")
