"""
================================================================================
 TRANG 8 — 👤 CUSTOMER ANALYTICS
================================================================================
Trả lời:
  1. Khách hàng của Affina là AI? (demographics)
  2. Ai là khách VIP? (RFM segmentation)
  3. Khách có quay lại mua không? (cohort retention)
  4. Khách mua sản phẩm này thường mua thêm gì? (cross-sell matrix)
  5. Bao nhiêu khách mua BHSK có thêm add-on? (product attachment)

Kỹ thuật DA áp dụng:
  • RFM Analysis (Recency-Frequency-Monetary)
  • Cohort retention analysis
  • Age band demographics
  • Cross-sell/Market basket analysis
  • Customer LTV estimation
================================================================================
"""
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.data import (
    COLORS, DATE_COL,
    apply_filters, apply_plotly_layout, empty_state,
    fmt_num, fmt_pct, fmt_vnd,
    load_master_data, render_sidebar_filters,
)

st.set_page_config(page_title="Customer Analytics", page_icon="👤", layout="wide")


# ============================================================================
# HELPERS
# ============================================================================
def _customer_id(df: pd.DataFrame) -> pd.Series:
    """Tạo ID khách unified. Ưu tiên CCCD NĐBH; fallback qua SĐT; fallback Tên+DOB."""
    id_col = pd.Series([None] * len(df), index=df.index, dtype=object)

    if "CCCD NĐBH" in df.columns:
        cccd = df["CCCD NĐBH"].astype(str).str.strip()
        cccd = cccd.replace(["", "nan", "None", "NaN", "0", "0.0"], np.nan)
        id_col = cccd

    # Fallback SĐT
    if "SĐT NMBH" in df.columns:
        sdt = df["SĐT NMBH"].astype(str).str.strip().str.replace(r"[^\d]", "", regex=True)
        sdt = sdt.replace(["", "nan"], np.nan)
        id_col = id_col.fillna(sdt)

    # Fallback Tên+DOB
    if "Tên NĐBH" in df.columns:
        name = df["Tên NĐBH"].astype(str).str.strip().str.upper()
        dob = pd.to_datetime(df.get("Ngày sinh NĐBH"), errors="coerce").dt.strftime("%Y%m%d").fillna("")
        combo = name + "_" + dob
        combo = combo.replace(["_", "NAN_"], np.nan)
        id_col = id_col.fillna(combo)

    return id_col


def _compute_age(dob_series: pd.Series, ref_date: pd.Timestamp = None) -> pd.Series:
    """Tính tuổi từ Ngày sinh, filter tuổi hợp lý (0-100)."""
    if ref_date is None:
        ref_date = pd.Timestamp.now()
    dob = pd.to_datetime(dob_series, errors="coerce")
    age = (ref_date - dob).dt.days / 365.25
    age = age.where((age >= 0) & (age <= 100))
    return age


def _rfm_score(series: pd.Series, reverse: bool = False) -> pd.Series:
    """Chia series thành 5 quintiles (1-5). reverse=True cho Recency (nhỏ = tốt)."""
    try:
        scores = pd.qcut(series.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
    except Exception:
        # Fallback nếu quá ít unique values
        scores = pd.Series(3, index=series.index)
    if reverse:
        scores = 6 - scores.astype(int)
    return scores.astype(int)


def _rfm_segment(row) -> str:
    """Phân loại segment dựa trên R, F, M score."""
    r, f, m = row["R"], row["F"], row["M"]
    fm = (f + m) / 2

    if r >= 4 and fm >= 4:  return "Champions 🏆"
    if r >= 3 and fm >= 3:  return "Loyal Customers 💎"
    if r >= 4 and fm <= 2:  return "New Customers 🆕"
    if r >= 3 and fm <= 2:  return "Potential Loyalists 🌱"
    if r <= 2 and fm >= 4:  return "At Risk (VIP) ⚠️"
    if r <= 2 and fm >= 3:  return "About to Sleep 😴"
    if r <= 2 and fm <= 2:  return "Lost 💔"
    if r == 3 and fm == 3:  return "Need Attention 👀"
    return "Others"


# ============================================================================
# MAIN
# ============================================================================
st.title("👤 Customer Analytics — Chân dung khách hàng Affina")
st.caption(
    "Phân tích: khách hàng là ai, ai là VIP, ai đang rời bỏ, "
    "khách mua sản phẩm gì cùng nhau."
)

df_all = load_master_data()
if df_all.empty:
    st.warning("Chưa có dữ liệu.")
    st.stop()

filters = render_sidebar_filters(df_all)
df = apply_filters(df_all, filters)
if df.empty:
    empty_state()
    st.stop()

# Add customer ID
df = df.copy()
df["_customer_id"] = _customer_id(df)
df_valid = df[df["_customer_id"].notna()].copy()

n_unique_cust = df_valid["_customer_id"].nunique()
n_records = len(df_valid)

# ==========================================================================
# 1. QUY MÔ KHÁCH HÀNG
# ==========================================================================
st.markdown("### 📊 Quy mô khách hàng")
c1, c2, c3, c4 = st.columns(4)
c1.metric("👥 Khách hàng duy nhất", fmt_num(n_unique_cust))
c2.metric("📋 Số HĐ", fmt_num(df["Số hợp đồng"].nunique() if "Số hợp đồng" in df else 0))
avg_hd_per_cust = n_records / n_unique_cust if n_unique_cust > 0 else 0
c3.metric("🔁 AVG HĐ/khách", f"{avg_hd_per_cust:.2f}",
           help="Cao > 1 = có tái mua/cross-sell tốt")
avg_rev_per_cust = df_valid["Doanh thu trước thuế"].sum() / n_unique_cust if n_unique_cust > 0 else 0
c4.metric("💰 AVG doanh thu/khách", fmt_vnd(avg_rev_per_cust, short=True))

# % identified
coverage = n_unique_cust / max(len(df), 1) * 100
if coverage < 60:
    st.warning(
        f"⚠️ Chỉ **{coverage:.0f}%** HĐ có thông tin định danh khách hàng (CCCD/SĐT/Tên). "
        f"Nên bổ sung CCCD/SĐT khi cấp đơn để tăng độ chính xác phân tích."
    )
else:
    st.success(f"✅ **{coverage:.0f}%** HĐ có thông tin định danh — data đủ tin cậy.")

st.divider()

# ==========================================================================
# 2. DEMOGRAPHICS
# ==========================================================================
st.markdown("### 🎂 Demographics — Chân dung khách hàng")

col_age, col_gender = st.columns([3, 2])

with col_age:
    st.markdown("**📈 Phân phối theo độ tuổi**")
    if "Ngày sinh NĐBH" in df_valid.columns:
        age = _compute_age(df_valid["Ngày sinh NĐBH"])
        age_df = pd.DataFrame({"age": age.dropna()})
        if not age_df.empty:
            # Bin thành nhóm tuổi
            bins = [0, 18, 25, 35, 45, 55, 65, 100]
            labels = ["Dưới 18", "18-25", "26-35", "36-45", "46-55", "56-65", "Trên 65"]
            age_df["group"] = pd.cut(age_df["age"], bins=bins, labels=labels, right=False)
            age_dist = age_df["group"].value_counts().sort_index()

            fig = px.bar(
                x=age_dist.index.astype(str),
                y=age_dist.values,
                text=age_dist.values,
                color=age_dist.values,
                color_continuous_scale="Blues",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                xaxis_title="Nhóm tuổi",
                yaxis_title="Số khách",
                showlegend=False,
                coloraxis_showscale=False,
                height=350,
            )
            st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

            # Insight
            top_group = age_dist.idxmax()
            top_pct = age_dist.max() / age_dist.sum() * 100
            avg_age = age.mean()
            st.caption(
                f"💡 Nhóm khách chính: **{top_group}** ({top_pct:.1f}%). "
                f"Độ tuổi TB: **{avg_age:.1f}** tuổi."
            )
        else:
            empty_state("Không có Ngày sinh hợp lệ.")
    else:
        empty_state("Không có cột 'Ngày sinh NĐBH'.")

with col_gender:
    st.markdown("**👫 Giới tính**")
    if "Giới tính NNBH" in df_valid.columns:
        gender = df_valid.groupby("_customer_id")["Giới tính NNBH"].first().value_counts()
        if not gender.empty:
            fig = px.pie(
                values=gender.values, names=gender.index,
                hole=0.5,
                color=gender.index,
                color_discrete_map={"Nam": "#3B82F6", "Nữ": "#EC4899"},
            )
            fig.update_traces(textposition="outside", textinfo="label+percent")
            st.plotly_chart(apply_plotly_layout(fig, title="", height=350),
                            use_container_width=True)

st.markdown("**🏠 Quan hệ với NMBH (Người mua BH)**")
if "Quan hệ" in df_valid.columns:
    rel = df_valid.groupby("Quan hệ", as_index=False).agg(
        n_customer=("_customer_id", "nunique"),
        revenue=("Doanh thu trước thuế", "sum"),
    ).sort_values("revenue", ascending=True)
    if not rel.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=rel["Quan hệ"], x=rel["n_customer"],
            orientation="h", name="Số khách",
            marker_color="#10B981",
            text=rel["n_customer"], textposition="outside",
        ))
        fig.update_layout(
            xaxis_title="Số khách hàng",
            height=max(250, 40 * len(rel)),
        )
        st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

st.divider()

# ==========================================================================
# 3. RFM SEGMENTATION
# ==========================================================================
st.markdown("### 💎 RFM Segmentation — Ai là khách VIP?")
st.caption(
    "**R**ecency (mua gần đây không?) · **F**requency (mua nhiều lần?) · "
    "**M**onetary (chi tiêu nhiều?). Phân loại 5×5 → 8 segments."
)

if DATE_COL in df_valid.columns and "Doanh thu trước thuế" in df_valid.columns:
    ref_date = df_valid[DATE_COL].max() + pd.Timedelta(days=1)

    rfm = df_valid.groupby("_customer_id").agg(
        recency=(DATE_COL, lambda x: (ref_date - x.max()).days),
        frequency=("Số hợp đồng", "nunique"),
        monetary=("Doanh thu trước thuế", "sum"),
    ).reset_index()
    rfm = rfm[rfm["monetary"] > 0]

    if len(rfm) >= 20:
        rfm["R"] = _rfm_score(rfm["recency"], reverse=True)
        rfm["F"] = _rfm_score(rfm["frequency"])
        rfm["M"] = _rfm_score(rfm["monetary"])
        rfm["segment"] = rfm.apply(_rfm_segment, axis=1)
        rfm["RFM_score"] = rfm["R"] * 100 + rfm["F"] * 10 + rfm["M"]

        # Segment summary
        seg_summary = rfm.groupby("segment").agg(
            n_customer=("_customer_id", "count"),
            total_revenue=("monetary", "sum"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
        ).sort_values("total_revenue", ascending=False)
        seg_summary["% khách"] = (seg_summary["n_customer"] / seg_summary["n_customer"].sum() * 100).round(1)
        seg_summary["% doanh thu"] = (seg_summary["total_revenue"] / seg_summary["total_revenue"].sum() * 100).round(1)

        # 2 cột: Treemap + Table
        col_tree, col_tbl = st.columns([3, 2])

        with col_tree:
            fig = px.treemap(
                seg_summary.reset_index(),
                path=["segment"],
                values="total_revenue",
                color="n_customer",
                color_continuous_scale="Viridis",
                hover_data={"n_customer": True, "avg_frequency": ":.1f", "avg_recency": ":.0f"},
            )
            fig.update_traces(
                textinfo="label+percent parent+value",
                texttemplate="<b>%{label}</b><br>%{percentParent} doanh thu<br>%{customdata[0]} khách",
            )
            st.plotly_chart(apply_plotly_layout(fig, title="Treemap Segment — kích thước ∝ doanh thu", height=450),
                            use_container_width=True)

        with col_tbl:
            st.markdown("**Chi tiết segments**")
            tbl = seg_summary[["n_customer", "% khách", "% doanh thu"]].copy()
            tbl.columns = ["Số khách", "% Khách", "% Doanh thu"]
            st.dataframe(tbl, use_container_width=True)

        # RFM Heatmap 5x5 (R × F)
        st.markdown("**🔥 Heatmap R × F — Distribution & Revenue**")
        col_a, col_b = st.columns(2)

        with col_a:
            heat_n = rfm.pivot_table(index="F", columns="R", values="_customer_id", aggfunc="count", fill_value=0)
            fig = px.imshow(
                heat_n, aspect="auto",
                labels=dict(x="R (Recency)", y="F (Frequency)", color="Số khách"),
                color_continuous_scale="Blues",
                text_auto=True,
            )
            fig.update_layout(height=350)
            st.plotly_chart(apply_plotly_layout(fig, title="Số lượng khách theo R × F"), use_container_width=True)

        with col_b:
            heat_m = rfm.pivot_table(index="F", columns="R", values="monetary", aggfunc="sum", fill_value=0)
            fig = px.imshow(
                heat_m, aspect="auto",
                labels=dict(x="R (Recency)", y="F (Frequency)", color="Doanh thu"),
                color_continuous_scale="YlOrRd",
                text_auto=".2s",
            )
            fig.update_layout(height=350)
            st.plotly_chart(apply_plotly_layout(fig, title="Doanh thu theo R × F"), use_container_width=True)

        # Insights
        champions = seg_summary[seg_summary.index.str.contains("Champions", na=False)]
        at_risk   = seg_summary[seg_summary.index.str.contains("At Risk", na=False)]
        if not champions.empty:
            st.success(
                f"🏆 **Champions** ({champions['n_customer'].values[0]:,} khách — "
                f"{champions['% khách'].values[0]:.1f}%) đang tạo ra "
                f"**{champions['% doanh thu'].values[0]:.1f}%** doanh thu. "
                f"→ Chương trình VIP care để giữ nhóm này."
            )
        if not at_risk.empty:
            st.warning(
                f"⚠️ **At Risk** ({at_risk['n_customer'].values[0]:,} khách VIP đang cách xa mua). "
                f"→ Chiến dịch win-back gấp để cứu **{fmt_vnd(at_risk['total_revenue'].values[0], short=True)}** doanh thu."
            )
    else:
        st.info("Cần ít nhất 20 khách hàng để RFM có ý nghĩa. Nới thời gian filter.")

st.divider()

# ==========================================================================
# 4. COHORT RETENTION
# ==========================================================================
st.markdown("### 🔁 Cohort Retention — Khách có quay lại mua không?")
st.caption(
    "Mỗi hàng = nhóm khách join tháng đó. Mỗi cột = % khách còn quay lại mua sau N tháng. "
    "Diagonal đỏ = mất khách nhanh. Cột cao dần bên phải = giữ chân tốt."
)

if DATE_COL in df_valid.columns:
    df_c = df_valid[df_valid["_customer_id"].notna()].copy()
    df_c["order_month"] = df_c[DATE_COL].dt.to_period("M").dt.to_timestamp()
    first_order = df_c.groupby("_customer_id")["order_month"].min().reset_index()
    first_order.columns = ["_customer_id", "cohort_month"]
    df_c = df_c.merge(first_order, on="_customer_id")
    df_c["months_since"] = (
        (df_c["order_month"].dt.year - df_c["cohort_month"].dt.year) * 12
        + (df_c["order_month"].dt.month - df_c["cohort_month"].dt.month)
    )

    cohort_data = (df_c.groupby(["cohort_month", "months_since"])["_customer_id"]
                        .nunique()
                        .reset_index())
    cohort_pivot = cohort_data.pivot_table(
        index="cohort_month", columns="months_since", values="_customer_id"
    )
    cohort_size = cohort_pivot.iloc[:, 0]
    retention = cohort_pivot.divide(cohort_size, axis=0) * 100

    # Limit to first 12 months for readability
    retention = retention.iloc[-24:, :13] if len(retention) > 24 else retention.iloc[:, :13]

    if not retention.empty:
        retention_display = retention.copy()
        retention_display.index = retention_display.index.strftime("%m/%Y")

        fig = px.imshow(
            retention_display.values,
            x=[f"M{i}" for i in retention_display.columns],
            y=retention_display.index,
            aspect="auto",
            color_continuous_scale="RdYlGn",
            zmin=0, zmax=100,
            text_auto=".0f",
            labels=dict(color="% Retention"),
        )
        fig.update_layout(
            xaxis_title="Tháng kể từ lần mua đầu",
            yaxis_title="Cohort (tháng khách vào)",
            height=max(400, 25 * len(retention_display)),
        )
        st.plotly_chart(apply_plotly_layout(fig, title="Cohort Retention (%)"), use_container_width=True)

        # Insight
        if retention.shape[1] > 1:
            avg_m1_retention = retention.iloc[:, 1].dropna().mean()
            if pd.notna(avg_m1_retention):
                if avg_m1_retention > 20:
                    st.success(f"✅ Retention tháng 1: **{avg_m1_retention:.1f}%** — tốt cho ngành BH.")
                else:
                    st.warning(
                        f"📉 Retention tháng 1 chỉ **{avg_m1_retention:.1f}%**. "
                        f"Đa số khách chỉ mua 1 lần — cần chiến lược cross-sell/tái tục."
                    )

st.divider()

# ==========================================================================
# 5. CROSS-SELL MATRIX
# ==========================================================================
st.markdown("### 🔀 Cross-sell Matrix — Khách mua A thường mua thêm gì?")
st.caption(
    "Ma trận đo affinity giữa các Loại BH. Ô đậm màu = khách mua Loại BH ở hàng "
    "thường mua thêm Loại BH ở cột."
)

if "Loại bảo hiểm" in df_valid.columns and n_unique_cust > 0:
    # Khách mua nhiều loại BH
    cust_types = df_valid.groupby("_customer_id")["Loại bảo hiểm"].apply(lambda s: set(s.dropna()))
    cust_types = cust_types[cust_types.apply(len) >= 1]

    # Tạo matrix
    all_types = sorted(df_valid["Loại bảo hiểm"].dropna().unique())
    matrix = pd.DataFrame(0, index=all_types, columns=all_types)

    for types_set in cust_types:
        types_list = list(types_set)
        for t1 in types_list:
            for t2 in types_list:
                if t1 != t2:
                    matrix.loc[t1, t2] += 1

    # Normalize by row (số khách mua loại hàng đó)
    row_totals = pd.Series({t: (cust_types.apply(lambda s: t in s)).sum() for t in all_types})
    matrix_pct = matrix.divide(row_totals.replace(0, np.nan), axis=0) * 100
    matrix_pct = matrix_pct.fillna(0).round(1)

    if matrix_pct.values.sum() > 0:
        fig = px.imshow(
            matrix_pct,
            aspect="auto",
            color_continuous_scale="Oranges",
            text_auto=True,
            labels=dict(x="Sản phẩm mua thêm", y="Sản phẩm mua đầu", color="% khách"),
        )
        fig.update_layout(height=450)
        st.plotly_chart(apply_plotly_layout(fig, title="Cross-sell affinity (%)"), use_container_width=True)

        # Top cross-sell pairs
        pairs = []
        for i in matrix_pct.index:
            for j in matrix_pct.columns:
                if i != j and matrix_pct.loc[i, j] > 0:
                    pairs.append((i, j, matrix_pct.loc[i, j], matrix.loc[i, j]))
        top_pairs = sorted(pairs, key=lambda x: -x[2])[:5]
        if top_pairs:
            st.markdown("**🎯 Top 5 cặp cross-sell mạnh nhất:**")
            for p in top_pairs:
                st.markdown(f"- Khách mua **{p[0]}** → **{p[2]:.1f}%** mua thêm **{p[1]}** ({int(p[3])} khách)")
    else:
        st.info("Chưa đủ dữ liệu cross-sell — cần khách mua ít nhất 2 loại BH.")

st.divider()

# ==========================================================================
# 6. BHSK ADD-ON ATTACHMENT
# ==========================================================================
st.markdown("### 🩺 BHSK Add-on Attachment Rate")
st.caption(
    "Trong các HĐ BHSK, bao nhiêu % có thêm add-on (Ngoại trú, Nha khoa, Thai sản, Topup)? "
    "Cross-sell là nguồn revenue phụ quan trọng."
)

df_bhsk = df[df.get("Loại bảo hiểm") == "BHSK"] if "Loại bảo hiểm" in df.columns else pd.DataFrame()
if not df_bhsk.empty:
    def _has_addon(x) -> bool:
        if pd.isna(x):
            return False
        v = str(x).strip().lower()
        if v in ("", "nan", "none", "0", "không", "khong", "no", "false"):
            return False
        return True

    n_bhsk = len(df_bhsk)
    rates = {}
    for col in ["Ngoại trú", "Nha khoa", "Thai sản", "Topup"]:
        if col in df_bhsk.columns:
            rates[col] = df_bhsk[col].apply(_has_addon).sum() / n_bhsk * 100

    if rates:
        col1, col2 = st.columns(2)

        with col1:
            r_df = pd.DataFrame({"Add-on": list(rates.keys()), "% attach": list(rates.values())})
            fig = px.bar(
                r_df, y="Add-on", x="% attach",
                orientation="h", color="% attach",
                color_continuous_scale="Blues",
                text="% attach",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(coloraxis_showscale=False, height=300)
            st.plotly_chart(apply_plotly_layout(fig, title=f"Trong {n_bhsk:,} HĐ BHSK"),
                            use_container_width=True)

        with col2:
            n_addons_per_contract = sum(
                df_bhsk[c].apply(_has_addon) for c in ["Ngoại trú", "Nha khoa", "Thai sản", "Topup"]
                if c in df_bhsk.columns
            )
            addon_dist = n_addons_per_contract.value_counts().sort_index()
            fig = px.pie(
                values=addon_dist.values, names=[f"{int(k)} add-on" for k in addon_dist.index],
                hole=0.5,
            )
            fig.update_traces(textposition="outside", textinfo="label+percent")
            st.plotly_chart(apply_plotly_layout(fig, title="Số add-on / HĐ", height=300),
                            use_container_width=True)

        # Insight
        avg_addons = n_addons_per_contract.mean()
        no_addon_pct = (n_addons_per_contract == 0).sum() / n_bhsk * 100
        st.caption(
            f"💡 **Insight**: TB **{avg_addons:.2f}** add-on/HĐ BHSK. "
            f"**{no_addon_pct:.1f}%** HĐ BHSK không có add-on nào — "
            f"cơ hội cross-sell rất lớn."
        )
else:
    st.info("Không có HĐ BHSK trong khoảng lọc.")

st.divider()
st.caption(
    "🧠 Trang này áp dụng: **RFM Segmentation** (5×5 grid), **Cohort Retention Analysis**, "
    "**Cross-sell/Market Basket**, **Demographic Profiling**, "
    "**Product Attachment Rate** — chuẩn CRM analytics."
)
