"""
================================================================================
 TRANG 6 — HEAD SALE DASHBOARD (An & Loan)
================================================================================
Dashboard chuyên biệt cho 2 Head Sale:
  • LD0991 — TRẦN THỊ THÙY AN (0909310495)
  • LD0894 — NGUYỄN THỊ HỒNG LOAN (0937431229)

Tính năng:
  1. Selector: xem nhánh An / Loan / Cả 2 (side-by-side)
  2. Toggle so sánh: OFF / Tháng trước / Năm trước
  3. 8 KPI cards với delta
  4. Hierarchy Sunburst: Head BDD BDM Sale
  5. Top 10 sale + rank movement (bump)
  6. BDD/BDM performance với sparkline
  7. Monthly trend + prev period overlay
  8. Product mix + comparison
  9. Alerts & Insights (anomaly detection)
 10. Contract Renewal Radar (HĐ sắp hết hạn)
 11. Team Health Index gauge
 12. Detail table + download CSV riêng cho nhánh
================================================================================
"""
import unicodedata

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

# ============================================================================
# CONFIG
# ============================================================================
st.set_page_config(page_title="Head Sale Dashboard", layout="wide")

from lib.auth import require_auth
require_auth("headsale", "Head Sale Dashboard")

from lib.theme import inject_css, render_header
inject_css()
render_header()

# Danh sách Head Sale (thêm/bớt trong tương lai — chỉ sửa dict này)
HEAD_SALES = {
    "TRẦN THỊ THÙY AN": {
        "code": "LD0991",
        "phone": "0909310495",
        "short": "An",
        "color": "#B44BC8", # xanh dương
    },
    "NGUYỄN THỊ HỒNG LOAN": {
        "code": "LD0894",
        "phone": "0937431229",
        "short": "Loan",
        "color": "#E8738F", # đỏ
    },
}

# Các cột có thể chứa tên Head Sale — thứ tự ưu tiên detect
HEAD_COL_CANDIDATES = [
    "Quản lý Cấp 3 (BDH)",
    "QUẢN LÝ CẤP 2 (BDD)",
    "QUẢN LÝ CẤP 1 (BDM)",
]


# ============================================================================
# HELPERS
# ============================================================================
def normalize_name(s) -> str:
    """Chuẩn hóa tên VN để so sánh: upper + strip + gộp space + normalize unicode."""
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFC", str(s)).strip().upper()
    return " ".join(s.split())


def find_head_column(df: pd.DataFrame) -> str | None:
    """Tìm cột chứa tên Head Sale — return tên cột hoặc None."""
    target_names = {normalize_name(k) for k in HEAD_SALES.keys()}
    for col in HEAD_COL_CANDIDATES:
        if col in df.columns:
            values_norm = df[col].dropna().apply(normalize_name).unique()
            if any(v in target_names for v in values_norm):
                return col
    return None


def filter_by_head(df: pd.DataFrame, head_col: str, head_name: str) -> pd.DataFrame:
    """Filter df theo tên head (dùng normalize để match linh hoạt)."""
    target = normalize_name(head_name)
    mask = df[head_col].apply(normalize_name) == target
    return df[mask]


def calc_prev_period(df_full: pd.DataFrame, filters: dict, mode: str) -> pd.DataFrame:
    """Tính data kỳ trước theo mode 'month' hoặc 'year'.
    Return df filtered theo kỳ trước với cùng các filter khác.
    """
    if mode == "off"or DATE_COL not in df_full.columns:
        return pd.DataFrame()

    start = pd.Timestamp(filters["start_date"])
    end = pd.Timestamp(filters["end_date"])

    if mode == "month":
        # cùng khoảng thời gian, dịch lùi đúng 1 tháng
        prev_start = start - pd.DateOffset(months=1)
        prev_end = end - pd.DateOffset(months=1)
    elif mode == "year":
        prev_start = start - pd.DateOffset(years=1)
        prev_end = end - pd.DateOffset(years=1)
    else:
        return pd.DataFrame()

    df_prev = df_full[
        (df_full[DATE_COL] >= prev_start) &
        (df_full[DATE_COL] <= prev_end + pd.Timedelta(days=1))
    ]
    # Áp cùng bộ lọc Source/Channel/Loại BH/Nhà BH
    if filters.get("sources"): df_prev = df_prev[df_prev["Source"].isin(filters["sources"])]
    if filters.get("channels"): df_prev = df_prev[df_prev["Channel"].isin(filters["channels"])]
    if filters.get("loai_bh"): df_prev = df_prev[df_prev["Loại bảo hiểm"].isin(filters["loai_bh"])]
    if filters.get("nha_bh"): df_prev = df_prev[df_prev["Nhà BH"].isin(filters["nha_bh"])]
    return df_prev


def compute_delta(cur: float, prev: float) -> str | None:
    """Trả về string delta '+X.X%' hoặc None nếu không tính được."""
    if prev is None or prev == 0 or pd.isna(prev):
        return None
    pct = (cur - prev) / prev * 100
    return f"{pct:+.1f}%"


def compute_health_index(df: pd.DataFrame, df_prev: pd.DataFrame | None) -> dict:
    """Tính Team Health Index 0-100 = Growth + Diversity + Coverage + Consistency."""
    scores = {}

    # Growth (30 pts): % change doanh thu vs prev
    cur_rev = df["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df else 0
    prev_rev = (df_prev["Doanh thu trước thuế"].sum()
                if df_prev is not None and not df_prev.empty and "Doanh thu trước thuế" in df_prev
                else 0)
    if prev_rev > 0:
        growth = (cur_rev - prev_rev) / prev_rev
        scores["growth"] = min(30, max(0, 15 + growth * 100)) # -15% 0đ, 0% 15đ, +15% 30đ
    else:
        scores["growth"] = 15 # neutral nếu không có kỳ trước

    # Diversity (25 pts): số loại BH trong nhánh
    if "Loại bảo hiểm" in df.columns:
        n_types = df["Loại bảo hiểm"].nunique()
        scores["diversity"] = min(25, n_types / 7 * 25) # 7 loại tối đa
    else:
        scores["diversity"] = 0

    # Coverage (25 pts): số sale có HĐ / tổng sale
    if "Họ tên sale" in df.columns:
        n_sales = df["Họ tên sale"].nunique()
        # Không có tổng sale để so tạm đánh giá bằng: sale >= 20 = 25 pts
        scores["coverage"] = min(25, n_sales / 20 * 25)
    else:
        scores["coverage"] = 0

    # Consistency (20 pts): CoV (coefficient of variation) doanh thu theo tuần thấp = ổn định
    if DATE_COL in df.columns and df[DATE_COL].notna().any():
        weekly = df.groupby(df[DATE_COL].dt.to_period("W"))["Doanh thu trước thuế"].sum()
        if len(weekly) >= 2 and weekly.mean() > 0:
            cov = weekly.std() / weekly.mean()
            scores["consistency"] = max(0, 20 - cov * 20) # cov càng thấp càng cao điểm
        else:
            scores["consistency"] = 10
    else:
        scores["consistency"] = 10

    total = sum(scores.values())
    return {**scores, "total": round(total, 1)}


def detect_alerts(df: pd.DataFrame, df_prev: pd.DataFrame | None) -> list[str]:
    """Phát hiện anomaly, return list các câu cảnh báo."""
    alerts = []
    today = pd.Timestamp.now()

    # 1. Sale doanh thu drop >50% so kỳ trước
    if df_prev is not None and not df_prev.empty and "Họ tên sale" in df.columns:
        cur = df.groupby("Họ tên sale")["Doanh thu trước thuế"].sum()
        prv = df_prev.groupby("Họ tên sale")["Doanh thu trước thuế"].sum()
        common = cur.index.intersection(prv.index)
        for name in common:
            if prv[name] > 0 and (cur[name] - prv[name]) / prv[name] < -0.5:
                alerts.append(
                    f"**Sale `{name}`**: doanh thu giảm "
                    f"**{((cur[name] - prv[name]) / prv[name] * 100):.0f}%** so kỳ trước "
                    f"({fmt_vnd(prv[name], short=True)} {fmt_vnd(cur[name], short=True)})"
                )
                if len(alerts) >= 3:
                    break

    # 2. Sale không active 14 ngày qua
    if DATE_COL in df.columns and "Họ tên sale" in df.columns and df[DATE_COL].notna().any():
        max_date = df[DATE_COL].max()
        cutoff = max_date - pd.Timedelta(days=14)
        last_activity = df.groupby("Họ tên sale")[DATE_COL].max()
        inactive = last_activity[last_activity < cutoff]
        if len(inactive) > 0:
            alerts.append(
                f"**{len(inactive)} sale** không có HĐ trong 14 ngày qua "
                f"(kể từ {cutoff.strftime('%d/%m/%Y')})"
            )

    # 3. HĐ sắp hết hạn 30 ngày
    if "Ngày kết thúc" in df.columns and df["Ngày kết thúc"].notna().any():
        expiring = df[
            (df["Ngày kết thúc"] > today) &
            (df["Ngày kết thúc"] <= today + pd.Timedelta(days=30))
        ]
        n_expiring = expiring["Số hợp đồng"].nunique() if "Số hợp đồng" in expiring else len(expiring)
        if n_expiring > 0:
            rev_at_risk = expiring["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in expiring else 0
            alerts.append(
                f"**{n_expiring} HĐ** sắp hết hạn trong 30 ngày tới "
                f"(giá trị: {fmt_vnd(rev_at_risk, short=True)}) — cần chiến dịch tái tục"
            )

    # 4. BDD có nhánh yếu (<3 sale active trong kỳ)
    if "QUẢN LÝ CẤP 2 (BDD)" in df.columns and "Họ tên sale" in df.columns:
        bdd_stats = df.groupby("QUẢN LÝ CẤP 2 (BDD)")["Họ tên sale"].nunique()
        weak_bdd = bdd_stats[bdd_stats < 3]
        if len(weak_bdd) > 0:
            names = ", ".join(f"`{n}`" for n in weak_bdd.index[:3])
            alerts.append(
                f"**{len(weak_bdd)} BDD** chỉ có <3 sale active: {names}"
                f"{'...' if len(weak_bdd) > 3 else ''}"
            )

    return alerts


def render_head_section(
    df_head: pd.DataFrame,
    df_head_prev: pd.DataFrame | None,
    head_name: str,
    head_info: dict,
    comparison_label: str,
) -> None:
    """Render toàn bộ chart cho 1 head sale. Được gọi 1 hoặc 2 lần tùy selector."""

    st.markdown(
        f"### {head_info['short']} — {head_name} "
        f"<span style='color:#666;font-size:14px'>({head_info['code']} · {head_info['phone']})</span>",
        unsafe_allow_html=True,
    )

    if df_head.empty:
        empty_state(
            f"Không có dữ liệu cho {head_info['short']} trong khoảng lọc hiện tại. "
            f"Thử nới rộng khoảng thời gian hoặc kiểm tra tên trong cột Head."
        )
        return

    # -----------------------------------------------------------------------
    # KPI CARDS
    # -----------------------------------------------------------------------
    cur = {
        "rev": df_head["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df_head else 0,
        "hd": df_head["Số hợp đồng"].nunique() if "Số hợp đồng" in df_head else 0,
        "sale": df_head["Họ tên sale"].nunique() if "Họ tên sale" in df_head else 0,
        "affina": df_head["Affina_Revenue"].sum() if "Affina_Revenue" in df_head else 0,
        "bonus": df_head["EST_Bonus"].sum() if "EST_Bonus" in df_head else 0,
        "prem": df_head["Phí BH (VNĐ)"].sum() if "Phí BH (VNĐ)" in df_head else 0,
    }
    cur["avg_hd"] = cur["rev"] / cur["hd"] if cur["hd"] > 0 else 0

    # Số sale active trong 14 ngày qua
    if DATE_COL in df_head.columns and df_head[DATE_COL].notna().any():
        cutoff = df_head[DATE_COL].max() - pd.Timedelta(days=14)
        active_recent = df_head[df_head[DATE_COL] >= cutoff]["Họ tên sale"].nunique()
    else:
        active_recent = 0

    # Delta
    prev = {}
    if df_head_prev is not None and not df_head_prev.empty:
        prev = {
            "rev": df_head_prev["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df_head_prev else 0,
            "hd": df_head_prev["Số hợp đồng"].nunique() if "Số hợp đồng" in df_head_prev else 0,
            "sale": df_head_prev["Họ tên sale"].nunique() if "Họ tên sale" in df_head_prev else 0,
            "affina": df_head_prev["Affina_Revenue"].sum() if "Affina_Revenue" in df_head_prev else 0,
            "bonus": df_head_prev["EST_Bonus"].sum() if "EST_Bonus" in df_head_prev else 0,
        }

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Doanh thu nhánh", fmt_vnd(cur["rev"], short=True),
              delta=compute_delta(cur["rev"], prev.get("rev")),
              help=f"So với {comparison_label}" if prev else None)
    c2.metric("Số HĐ", fmt_num(cur["hd"]),
              delta=compute_delta(cur["hd"], prev.get("hd")))
    c3.metric("Sale trong nhánh", fmt_num(cur["sale"]),
              delta=compute_delta(cur["sale"], prev.get("sale")))
    c4.metric("Affina Revenue", fmt_vnd(cur["affina"], short=True),
              delta=compute_delta(cur["affina"], prev.get("affina")))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("EST Bonus", fmt_vnd(cur["bonus"], short=True),
              delta=compute_delta(cur["bonus"], prev.get("bonus")))
    c6.metric("Phí BH", fmt_vnd(cur["prem"], short=True))
    c7.metric("AVG DT/HĐ", fmt_vnd(cur["avg_hd"], short=True))
    c8.metric("Sale active 14d", fmt_num(active_recent),
              help="Số sale có ít nhất 1 HĐ trong 14 ngày gần nhất")

    st.markdown("")

    # -----------------------------------------------------------------------
    # TEAM HEALTH INDEX (gauge) + ALERTS
    # -----------------------------------------------------------------------
    col_health, col_alerts = st.columns([1, 2])

    with col_health:
        st.markdown("** Team Health Index**")
        health = compute_health_index(df_head, df_head_prev)
        gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health["total"],
            number={"suffix": " /100", "font": {"size": 32}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": head_info["color"]},
                "steps": [
                    {"range": [0, 40], "color": "#FEE2E2"},
                    {"range": [40, 70], "color": "#FEF3C7"},
                    {"range": [70, 100], "color": "#D1FAE5"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 2},
                    "thickness": 0.75,
                    "value": 70,
                },
            },
        ))
        gauge.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(gauge, use_container_width=True)
        st.caption(
            f"Growth: **{health['growth']:.0f}/30** · Diversity: **{health['diversity']:.0f}/25** · "
            f"Coverage: **{health['coverage']:.0f}/25** · Consistency: **{health['consistency']:.0f}/20**"
        )

    with col_alerts:
        st.markdown("** Alerts & Insights**")
        alerts = detect_alerts(df_head, df_head_prev)
        if alerts:
            for a in alerts[:5]:
                st.warning(a)
        else:
            st.success("Không có cảnh báo bất thường trong kỳ này.")

    st.divider()

    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # TOP SALES TRONG NHANH (thay sunburst) + Product mix (thay pie)
    # -----------------------------------------------------------------------

    # Filter theo thang/nam cho section nay
    st.markdown("**Top Sales trong nhanh**")
    tf_col1, tf_col2, tf_col3 = st.columns([1, 1, 1])
    with tf_col1:
        top_n_opt = st.radio(
            "Hien thi", options=["Top 5", "Top 10", "Top 20"],
            horizontal=True, key=f"head_topn_{head_info['short']}",
        )
        top_n = int(top_n_opt.split(" ")[1])
    with tf_col2:
        if DATE_COL in df_head.columns and df_head[DATE_COL].notna().any():
            years_avail = sorted(df_head[DATE_COL].dt.year.dropna().unique().astype(int))
            year_filter = st.selectbox(
                "Nam", options=["Tat ca"] + [str(y) for y in years_avail],
                key=f"head_year_{head_info['short']}",
            )
        else:
            year_filter = "Tat ca"
    with tf_col3:
        if year_filter != "Tat ca" and DATE_COL in df_head.columns:
            months_avail = sorted(
                df_head[df_head[DATE_COL].dt.year == int(year_filter)][DATE_COL]
                .dt.month.dropna().unique().astype(int)
            )
            month_filter = st.selectbox(
                "Thang", options=["Tat ca"] + [str(m) for m in months_avail],
                key=f"head_month_{head_info['short']}",
            )
        else:
            month_filter = "Tat ca"

    # Apply time filter
    df_filtered_head = df_head.copy()
    if year_filter != "Tat ca" and DATE_COL in df_filtered_head.columns:
        df_filtered_head = df_filtered_head[df_filtered_head[DATE_COL].dt.year == int(year_filter)]
    if month_filter != "Tat ca" and DATE_COL in df_filtered_head.columns:
        df_filtered_head = df_filtered_head[df_filtered_head[DATE_COL].dt.month == int(month_filter)]

    col_top, col_mix = st.columns([3, 2])

    with col_top:
        if "Họ tên sale" in df_filtered_head.columns and not df_filtered_head.empty:
            top_df = (df_filtered_head.groupby("Họ tên sale", as_index=False)
                          .agg(revenue=("Doanh thu trước thuế", "sum"),
                               n_hd=("Số hợp đồng", "nunique"))
                          .sort_values("revenue", ascending=True)
                          .tail(top_n))
            if not top_df.empty:
                fig = px.bar(
                    top_df, x="revenue", y="Họ tên sale",
                    orientation="h", text_auto=".2s",
                    color="revenue",
                    color_continuous_scale=["#F9EBF7", "#E85BD8", "#B44BC8", "#7D2E78"],
                    hover_data={"n_hd": True},
                )
                fig.update_layout(coloraxis_showscale=False, yaxis_title="")
                fig.update_xaxes(title="Doanh thu (VND)", tickformat=",")
                period_label = ""
                if year_filter != "Tat ca":
                    period_label = f" — {year_filter}"
                if month_filter != "Tat ca":
                    period_label += f"/{month_filter}"
                st.plotly_chart(
                    apply_plotly_layout(fig, title=f"{top_n_opt} Sales{period_label}", height=max(350, top_n * 35)),
                    use_container_width=True,
                )
            else:
                empty_state("Khong co data sau filter.")
        else:
            empty_state()

    with col_mix:
        st.markdown("**Loai bao hiem**")
        if "Loại bảo hiểm" in df_filtered_head.columns and not df_filtered_head.empty:
            mix = (df_filtered_head.groupby("Loại bảo hiểm", as_index=False)["Doanh thu trước thuế"]
                       .sum().sort_values("Doanh thu trước thuế", ascending=True))
            mix = mix[mix["Doanh thu trước thuế"] > 0]
            if not mix.empty:
                fig = px.bar(
                    mix, x="Doanh thu trước thuế", y="Loại bảo hiểm",
                    orientation="h", text_auto=".2s",
                    color="Loại bảo hiểm", color_discrete_map=COLORS,
                )
                fig.update_layout(showlegend=False, yaxis_title="")
                fig.update_xaxes(title="Doanh thu (VND)", tickformat=",")
                st.plotly_chart(
                    apply_plotly_layout(fig, title="", height=350),
                    use_container_width=True,
                )

    st.divider()

    # -----------------------------------------------------------------------
    # TREND THEO THÁNG + OVERLAY KỲ TRƯỚC
    # -----------------------------------------------------------------------
    st.markdown("** Doanh thu theo tháng** (kỳ hiện tại vs kỳ trước)")
    if DATE_COL in df_head.columns and df_head[DATE_COL].notna().any():
        df_m = df_head.copy()
        df_m["month"] = df_m[DATE_COL].dt.to_period("M").dt.to_timestamp()
        cur_monthly = df_m.groupby("month", as_index=False)["Doanh thu trước thuế"].sum()
        cur_monthly["Kỳ"] = "Kỳ này"

        if df_head_prev is not None and not df_head_prev.empty:
            df_p = df_head_prev.copy()
            df_p["month"] = df_p[DATE_COL].dt.to_period("M").dt.to_timestamp()
            prv_monthly = df_p.groupby("month", as_index=False)["Doanh thu trước thuế"].sum()
            prv_monthly["Kỳ"] = comparison_label
            combined = pd.concat([cur_monthly, prv_monthly], ignore_index=True)
        else:
            combined = cur_monthly

        if not combined.empty:
            fig = px.bar(
                combined, x="month", y="Doanh thu trước thuế", color="Kỳ",
                barmode="group",
                color_discrete_map={"Kỳ này": head_info["color"], comparison_label: "#C9B8D6"},
                labels={"month": "Tháng", "Doanh thu trước thuế": "Doanh thu (VNĐ)"},
            )
            fig.update_yaxes(tickformat=",.0f")
            fig.update_xaxes(dtick="M1", tickformat="%m/%Y")
            st.plotly_chart(
                apply_plotly_layout(fig, title="", height=380),
                use_container_width=True,
            )

    st.divider()

    # -----------------------------------------------------------------------
    # TOP 10 SALE + RANK MOVEMENT
    # -----------------------------------------------------------------------
    st.markdown("** Top 10 Sale doanh thu cao nhất**")
    if "Họ tên sale" in df_head.columns:
        cur_ranked = (df_head.groupby("Họ tên sale", as_index=False)
                             .agg(revenue=("Doanh thu trước thuế", "sum"),
                                  n_hd=("Số hợp đồng", "nunique"),
                                  bonus=("EST_Bonus", "sum"))
                             .sort_values("revenue", ascending=False)
                             .head(10)
                             .reset_index(drop=True))
        cur_ranked["rank_now"] = cur_ranked.index + 1

        # Compute prev rank
        if df_head_prev is not None and not df_head_prev.empty:
            prev_ranked = (df_head_prev.groupby("Họ tên sale", as_index=False)
                                        ["Doanh thu trước thuế"].sum()
                                        .sort_values("Doanh thu trước thuế", ascending=False)
                                        .reset_index(drop=True))
            prev_ranked["rank_prev"] = prev_ranked.index + 1
            cur_ranked = cur_ranked.merge(
                prev_ranked[["Họ tên sale", "rank_prev"]],
                on="Họ tên sale", how="left"
            )
        else:
            cur_ranked["rank_prev"] = None

        # Build display columns
        def _rank_movement(row):
            if pd.isna(row["rank_prev"]):
                return "Mới"
            diff = int(row["rank_prev"]) - int(row["rank_now"])
            if diff > 0: return f"▲ +{diff}"
            if diff < 0: return f"▼ {diff}"
            return "= 0"

        cur_ranked["Thứ hạng"] = cur_ranked["rank_now"].astype(int)
        cur_ranked["Chuyển động"] = cur_ranked.apply(_rank_movement, axis=1)
        cur_ranked["Doanh thu"] = cur_ranked["revenue"].apply(lambda v: fmt_vnd(v, short=True))
        cur_ranked["Số HĐ"] = cur_ranked["n_hd"].apply(fmt_num)
        cur_ranked["EST_Bonus"] = cur_ranked["bonus"].apply(lambda v: fmt_vnd(v, short=True))

        display_cols = ["Thứ hạng", "Họ tên sale", "Chuyển động", "Số HĐ", "Doanh thu", "EST_Bonus"]
        st.dataframe(
            cur_ranked[display_cols],
            hide_index=True, use_container_width=True,
        )
        st.caption(
            "▲ = tăng hạng · ▼ = giảm hạng · (=) giữ nguyên · Mới = mới vào top 10"
            f"{' (so với ' + comparison_label + ')' if not cur_ranked['rank_prev'].isna().all() else ''}"
        )
    st.markdown("")

    # -----------------------------------------------------------------------
    # BDD PERFORMANCE
    # -----------------------------------------------------------------------
    st.markdown("** Hiệu suất BDD trong nhánh**")
    if "QUẢN LÝ CẤP 2 (BDD)" in df_head.columns:
        bdd_perf = (df_head.groupby("QUẢN LÝ CẤP 2 (BDD)", as_index=False)
                            .agg(revenue=("Doanh thu trước thuế", "sum"),
                                 n_sale=("Họ tên sale", "nunique"),
                                 n_hd=("Số hợp đồng", "nunique"),
                                 affina=("Affina_Revenue", "sum"))
                            .sort_values("revenue", ascending=False))

        if not bdd_perf.empty:
            fig = px.bar(
                bdd_perf, x="revenue", y="QUẢN LÝ CẤP 2 (BDD)",
                orientation="h",
                color="revenue", color_continuous_scale=["#FDF2FB", "#F0AEE2", "#D06DC4", "#A6409E", "#7D2E78"],
                labels={"revenue": "Doanh thu (VNĐ)", "QUẢN LÝ CẤP 2 (BDD)": "BDD"},
                hover_data={"n_sale": True, "n_hd": True},
            )
            fig.update_yaxes(categoryorder="total ascending")
            fig.update_xaxes(tickformat=",.0f")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(
                apply_plotly_layout(fig, title="", height=max(300, 40 * len(bdd_perf))),
                use_container_width=True,
            )

    st.divider()

    # -----------------------------------------------------------------------
    # CONTRACT RENEWAL RADAR (HĐ sắp hết hạn)
    # -----------------------------------------------------------------------
    st.markdown("** Contract Renewal Radar** — HĐ sắp hết hạn (mỏ vàng doanh thu tái tục)")
    if "Ngày kết thúc" in df_head.columns and df_head["Ngày kết thúc"].notna().any():
        today = pd.Timestamp.now().normalize()
        buckets = [
            ("Trong 7 ngày", 1, 7, "#C93DA8"),
            ("8-15 ngày", 8, 15, "#EDB16E"),
            ("16-30 ngày", 16, 30, "#D9A0C4"),
            ("31-60 ngày", 31, 60, "#5FBFA0"),
            ("61-90 ngày", 61, 90, "#B44BC8"),
        ]
        rows = []
        for label, d1, d2, color in buckets:
            start = today + pd.Timedelta(days=d1)
            end = today + pd.Timedelta(days=d2)
            mask = (df_head["Ngày kết thúc"] >= start) & (df_head["Ngày kết thúc"] <= end)
            df_bucket = df_head[mask]
            rows.append({
                "Khoảng thời gian": label,
                "Số HĐ": df_bucket["Số hợp đồng"].nunique() if "Số hợp đồng" in df_bucket else len(df_bucket),
                "Giá trị (VNĐ)": df_bucket["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df_bucket else 0,
                "color": color,
            })
        df_renew = pd.DataFrame(rows)

        col_a, col_b = st.columns(2)
        with col_a:
            fig = go.Figure(go.Bar(
                x=df_renew["Số HĐ"],
                y=df_renew["Khoảng thời gian"],
                orientation="h",
                marker_color=df_renew["color"],
                text=df_renew["Số HĐ"],
                textposition="outside",
            ))
            fig.update_layout(
                title="Số HĐ theo bucket thời gian",
                xaxis_title="Số hợp đồng",
                height=320,
            )
            st.plotly_chart(apply_plotly_layout(fig, title="Số HĐ theo bucket", height=320),
                            use_container_width=True)

        with col_b:
            fig2 = go.Figure(go.Bar(
                x=df_renew["Giá trị (VNĐ)"],
                y=df_renew["Khoảng thời gian"],
                orientation="h",
                marker_color=df_renew["color"],
                text=[fmt_vnd(v, short=True) for v in df_renew["Giá trị (VNĐ)"]],
                textposition="outside",
            ))
            fig2.update_layout(
                title="Giá trị HĐ theo bucket",
                xaxis_title="Doanh thu (VNĐ)",
                xaxis_tickformat=",.0f",
                height=320,
            )
            st.plotly_chart(apply_plotly_layout(fig2, title="Giá trị HĐ theo bucket", height=320),
                            use_container_width=True)

        total_renew_hd = df_renew["Số HĐ"].sum()
        total_renew_val = df_renew["Giá trị (VNĐ)"].sum()
        st.info(
            f"**Tổng cơ hội tái tục 90 ngày tới**: **{total_renew_hd:,} HĐ** — "
            f"giá trị **{fmt_vnd(total_renew_val, short=True)}**. "
            f"Nên khởi động chiến dịch remind trước 30 ngày."
        )
    else:
        empty_state("Không có cột 'Ngày kết thúc' để tính renewal radar.")

    st.divider()

    # -----------------------------------------------------------------------
    # DETAIL TABLE + DOWNLOAD
    # -----------------------------------------------------------------------
    with st.expander(f"Xem bảng chi tiết & tải CSV cho nhánh {head_info['short']}"):
        show_cols = [c for c in [
            "Ngày thanh toán", "Số hợp đồng", "Họ tên sale",
            "QUẢN LÝ CẤP 1 (BDM)", "QUẢN LÝ CẤP 2 (BDD)",
            "Loại bảo hiểm", "Sản phẩm", "Nhà BH",
            "Số tiền thanh toán", "Doanh thu trước thuế", "Affina_Revenue", "EST_Bonus",
        ] if c in df_head.columns]
        st.dataframe(
            df_head[show_cols].sort_values(DATE_COL, ascending=False) if DATE_COL in show_cols else df_head[show_cols],
            hide_index=True, use_container_width=True, height=350,
        )
        csv = df_head[show_cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            f"Tải CSV — nhánh {head_info['short']} ({len(df_head):,} dòng)",
            data=csv,
            file_name=f"nhanh_{head_info['short']}_{pd.Timestamp.now():%Y%m%d}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ============================================================================
# MAIN
# ============================================================================
st.title("Head Sale Dashboard — An & Loan")
st.caption(
    "Dashboard chuyên biệt cho 2 Head Sale, "
    "phân tích hiệu suất nhánh + phát hiện anomaly + cơ hội tái tục."
)

# Load
df_all = load_master_data()
if df_all.empty:
    st.warning("Chưa có dữ liệu trong `dashboard_master_data`.")
    st.stop()

# Detect head column
head_col = find_head_column(df_all)
if head_col is None:
    st.error(
        "**Không tìm thấy tên Head Sale** trong các cột "
        f"{HEAD_COL_CANDIDATES} của bảng `dashboard_master_data`.\n\n"
        "**Có thể do:**\n"
        "1. Nhánh An/Loan chưa đủ dữ liệu trong khoảng 2024-2026\n"
        "2. Tên trong DSNS có dấu/spacing khác với config trong file này\n\n"
        "**Cách kiểm tra:** vào Supabase Studio SQL Editor chạy:\n"
        "```sql\n"
        "SELECT DISTINCT \"Quản lý Cấp 3 (BDH)\" FROM dashboard_master_data\n"
        "WHERE \"Quản lý Cấp 3 (BDH)\" IS NOT NULL LIMIT 20;\n"
        "```"
    )
    st.stop()

st.caption(f"Cột chứa Head Sale được detect: **`{head_col}`**")

# Common filters (từ lib/data.py — nhớ import session_state để không reset)
filters = render_sidebar_filters(df_all)
df_filtered = apply_filters(df_all, filters)

# ============================================================================
# HEAD SELECTOR + COMPARISON MODE (sidebar)
# ============================================================================
st.sidebar.divider()
st.sidebar.markdown("### Head Sale View")

view_mode = st.sidebar.radio(
    "Xem nhánh:",
    options=["Cả 2 (side-by-side)", "TRẦN THỊ THÙY AN", "NGUYỄN THỊ HỒNG LOAN"],
    format_func=lambda x: {
        "Cả 2 (side-by-side)": " Cả 2",
        "TRẦN THỊ THÙY AN": " An (LD0991)",
        "NGUYỄN THỊ HỒNG LOAN": " Loan (LD0894)",
    }.get(x, x),
    key="head_view_mode",
)

comp_mode = st.sidebar.radio(
    "So sánh với:",
    options=["off", "month", "year"],
    format_func=lambda x: {
        "off": "Tắt so sánh",
        "month": " Kỳ trước (tháng)",
        "year": " Cùng kỳ năm trước",
    }[x],
    key="head_comp_mode",
)

comparison_label = {
    "off": "",
    "month": "Kỳ trước",
    "year": "Cùng kỳ năm trước",
}[comp_mode]

# Compute prev period df (once, reuse for both heads)
df_prev_all = calc_prev_period(df_all, filters, comp_mode) if comp_mode != "off"else pd.DataFrame()

# ============================================================================
# RENDER
# ============================================================================
if view_mode == "Cả 2 (side-by-side)":
    st.info(
        "Chế độ so sánh 2 nhánh song song. Cuộn xuống để xem chi tiết từng head. "
        "Muốn xem sâu 1 nhánh chọn ở sidebar bên trái."
    )

    # Bảng tổng An vs Loan
    st.markdown("### So sánh nhanh An vs Loan")
    summary_rows = []
    for head_name, head_info in HEAD_SALES.items():
        df_head = filter_by_head(df_filtered, head_col, head_name)
        summary_rows.append({
            "Head": f"{head_info['short']} ({head_info['code']})",
            "Doanh thu": df_head["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df_head else 0,
            "Số HĐ": df_head["Số hợp đồng"].nunique() if "Số hợp đồng" in df_head else 0,
            "Số Sale": df_head["Họ tên sale"].nunique() if "Họ tên sale" in df_head else 0,
            "Affina Rev": df_head["Affina_Revenue"].sum() if "Affina_Revenue" in df_head else 0,
        })
    df_sum = pd.DataFrame(summary_rows)
    df_sum_disp = df_sum.copy()
    df_sum_disp["Doanh thu"] = df_sum_disp["Doanh thu"].apply(lambda v: fmt_vnd(v, short=True))
    df_sum_disp["Số HĐ"] = df_sum_disp["Số HĐ"].apply(fmt_num)
    df_sum_disp["Số Sale"] = df_sum_disp["Số Sale"].apply(fmt_num)
    df_sum_disp["Affina Rev"] = df_sum_disp["Affina Rev"].apply(lambda v: fmt_vnd(v, short=True))
    st.dataframe(df_sum_disp, hide_index=True, use_container_width=True)

    # Bar chart 4 metric side-by-side
    df_sum_melt = df_sum.melt(id_vars=["Head"], var_name="Chỉ số", value_name="Giá trị")
    fig_sum = px.bar(
        df_sum_melt, x="Chỉ số", y="Giá trị", color="Head",
        barmode="group",
        color_discrete_map={
            f"An ({HEAD_SALES['TRẦN THỊ THÙY AN']['code']})": HEAD_SALES["TRẦN THỊ THÙY AN"]["color"],
            f"Loan ({HEAD_SALES['NGUYỄN THỊ HỒNG LOAN']['code']})": HEAD_SALES["NGUYỄN THỊ HỒNG LOAN"]["color"],
        },
    )
    fig_sum.update_yaxes(tickformat=",.0f")
    st.plotly_chart(apply_plotly_layout(fig_sum, title="", height=380),
                    use_container_width=True)

    st.divider()

    # Render từng head
    for head_name, head_info in HEAD_SALES.items():
        df_head = filter_by_head(df_filtered, head_col, head_name)
        df_head_prev = filter_by_head(df_prev_all, head_col, head_name) if not df_prev_all.empty else None
        render_head_section(df_head, df_head_prev, head_name, head_info, comparison_label or "Kỳ trước")
        st.markdown("---")

else:
    # Single head view
    head_name = view_mode
    head_info = HEAD_SALES[head_name]
    df_head = filter_by_head(df_filtered, head_col, head_name)
    df_head_prev = filter_by_head(df_prev_all, head_col, head_name) if not df_prev_all.empty else None
    render_head_section(df_head, df_head_prev, head_name, head_info, comparison_label or "Kỳ trước")

st.divider()
st.caption(
    "**Tip cho Head:** dùng khoảng thời gian ở sidebar để zoom vào 1 tháng, "
    "bật 'So sánh với Cùng kỳ năm trước' để đánh giá growth thật, "
    "và check phần **Renewal Radar** hàng tuần để không bỏ lỡ cơ hội tái tục."
)
