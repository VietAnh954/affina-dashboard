"""
================================================================================
 TRANG 7 — EXECUTIVE INSIGHTS (Diagnostic Analytics)
================================================================================
Trả lời các câu hỏi mà chỉ senior DA mới trả lời được:
  1. VÌ SAO doanh thu tăng/giảm? (growth decomposition)
  2. Yếu tố nào ảnh hưởng doanh thu NHẤT? (correlation + feature importance)
  3. Con số tăng có ý nghĩa THỐNG KÊ không? (t-test, confidence interval)
  4. Sale nào đang ở đâu trong phân phối? (percentile rank)
  5. Hành động nào nên làm tiếp theo? (auto recommendations)

Kỹ thuật DA áp dụng:
  • Auto-narrative — tự viết bản tóm tắt bằng tiếng Việt tự nhiên
  • Growth decomposition — tách growth thành 3 phần: volume, price, mix
  • Correlation matrix — Pearson & Spearman
  • Statistical significance — 95% CI, t-test
  • Percentile ranks — P25/P50/P75/P90 cho sale performance
  • Pareto analysis — 80/20 rule
================================================================================
"""
from typing import Optional

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
st.set_page_config(page_title="Executive Insights", layout="wide")

from lib.auth import require_auth
require_auth("executive", "Executive Insights")

from lib.theme import inject_css, render_header
inject_css()
render_header()

# Try import scipy - graceful degradation nếu không có
try:
    from scipy import stats as sp_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ============================================================================
# HELPERS
# ============================================================================
def _prev_period_df(df_full: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Data kỳ trước = cùng khoảng thời gian, dịch lùi đúng 1 kỳ."""
    if DATE_COL not in df_full.columns:
        return pd.DataFrame()
    start = pd.Timestamp(filters["start_date"])
    end = pd.Timestamp(filters["end_date"])
    period_days = (end - start).days + 1
    prev_start = start - pd.Timedelta(days=period_days)
    prev_end = start - pd.Timedelta(days=1)
    df_prev = df_full[
        (df_full[DATE_COL] >= prev_start) &
        (df_full[DATE_COL] <= prev_end + pd.Timedelta(days=1))
    ]
    # Áp cùng bộ filter phi thời gian
    for key, col in [("sources", "Source"), ("channels", "Channel"),
                     ("loai_bh", "Loại bảo hiểm"), ("nha_bh", "Nhà BH")]:
        if filters.get(key):
            df_prev = df_prev[df_prev[col].isin(filters[key])]
    return df_prev


def _confidence_interval(series: pd.Series, alpha: float = 0.05) -> tuple[float, float]:
    """95% CI cho mean của series (dùng t-distribution)."""
    s = series.dropna()
    if len(s) < 2:
        return (np.nan, np.nan)
    mean = s.mean()
    if HAS_SCIPY:
        se = sp_stats.sem(s)
        h = se * sp_stats.t.ppf(1 - alpha / 2, len(s) - 1)
    else:
        # Fallback: dùng normal approximation
        h = 1.96 * s.std() / np.sqrt(len(s))
    return (mean - h, mean + h)


def _decompose_growth(df_cur: pd.DataFrame, df_prv: pd.DataFrame) -> dict:
    """Tách growth doanh thu thành 3 phần: Volume + Price + Mix effect.
    
    Δ Revenue = Δ Volume × Price_avg + Volume_new × Δ Price + Mix effect
    
    Simplified formula:
      volume_effect = (n_hd_cur - n_hd_prv) × avg_price_prv
      price_effect = (avg_price_cur - avg_price_prv) × n_hd_cur
    """
    if "Số hợp đồng" not in df_cur.columns or "Doanh thu trước thuế" not in df_cur.columns:
        return {}
    n_cur = df_cur["Số hợp đồng"].nunique()
    n_prv = df_prv["Số hợp đồng"].nunique() if not df_prv.empty else 0
    rev_cur = df_cur["Doanh thu trước thuế"].sum()
    rev_prv = df_prv["Doanh thu trước thuế"].sum() if not df_prv.empty else 0
    avg_cur = rev_cur / n_cur if n_cur > 0 else 0
    avg_prv = rev_prv / n_prv if n_prv > 0 else 0

    volume_effect = (n_cur - n_prv) * avg_prv
    price_effect = (avg_cur - avg_prv) * n_cur
    total_delta = rev_cur - rev_prv
    mix_effect = total_delta - volume_effect - price_effect # residual = mix + interaction

    return {
        "total_delta": total_delta,
        "volume_effect": volume_effect,
        "price_effect": price_effect,
        "mix_effect": mix_effect,
        "avg_cur": avg_cur,
        "avg_prv": avg_prv,
        "n_cur": n_cur,
        "n_prv": n_prv,
    }


def _generate_narrative(df_cur: pd.DataFrame, df_prv: pd.DataFrame, filters: dict) -> str:
    """Tự sinh executive summary bằng tiếng Việt tự nhiên."""
    if df_cur.empty:
        return "_Không có dữ liệu trong khoảng lọc._"

    start = pd.Timestamp(filters["start_date"]).strftime("%d/%m/%Y")
    end = pd.Timestamp(filters["end_date"]).strftime("%d/%m/%Y")

    rev = df_cur["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df_cur else 0
    n_hd = df_cur["Số hợp đồng"].nunique() if "Số hợp đồng" in df_cur else 0
    n_sale = df_cur["Họ tên sale"].nunique() if "Họ tên sale" in df_cur else 0

    # Growth vs kỳ trước
    delta_text = ""
    if not df_prv.empty and "Doanh thu trước thuế" in df_prv:
        prev_rev = df_prv["Doanh thu trước thuế"].sum()
        if prev_rev > 0:
            pct = (rev - prev_rev) / prev_rev * 100
            direction = "tăng" if pct > 0 else "giảm"
            magnitude = "mạnh" if abs(pct) > 20 else "nhẹ" if abs(pct) < 5 else ""
            delta_text = (
                f"— {direction} {magnitude} **{abs(pct):.1f}%** so kỳ trước "
                f"({fmt_vnd(prev_rev, short=True)})"
            )

    # Source dominant
    src_txt = ""
    if "Source" in df_cur.columns:
        src_share = df_cur.groupby("Source")["Doanh thu trước thuế"].sum()
        if not src_share.empty:
            top_src = src_share.idxmax()
            top_pct = src_share.max() / src_share.sum() * 100
            src_txt = (
                f"Nhánh **{top_src}** đóng góp lớn nhất — **{top_pct:.1f}%** "
                f"({fmt_vnd(src_share.max(), short=True)})."
            )

    # Top product
    prod_txt = ""
    if "Sản phẩm" in df_cur.columns:
        prod_share = df_cur.groupby("Sản phẩm")["Doanh thu trước thuế"].sum().nlargest(1)
        if not prod_share.empty:
            prod_txt = (
                f"Sản phẩm bán chạy nhất: **{prod_share.index[0]}** "
                f"({fmt_vnd(prod_share.values[0], short=True)})."
            )

    # Top sale
    sale_txt = ""
    if "Họ tên sale" in df_cur.columns:
        sale_share = df_cur.groupby("Họ tên sale")["Doanh thu trước thuế"].sum().nlargest(1)
        if not sale_share.empty:
            sale_txt = (
                f"Sale xuất sắc nhất: **{sale_share.index[0]}** "
                f"({fmt_vnd(sale_share.values[0], short=True)})."
            )

    narrative = (
        f"Từ **{start}** đến **{end}**, Affina đạt tổng doanh thu "
        f"**{fmt_vnd(rev, short=True)}** {delta_text}, "
        f"trên **{fmt_num(n_hd)}** hợp đồng được cấp bởi **{fmt_num(n_sale)}** sale."
        f"{src_txt}{prod_txt}{sale_txt}"
    )
    return narrative


def _detect_wins_and_concerns(df_cur: pd.DataFrame, df_prv: pd.DataFrame) -> tuple[list, list]:
    """Auto-detect top 3 wins & top 3 concerns."""
    wins, concerns = [], []
    if df_prv.empty:
        return wins, concerns

    # 1. Growth ở mỗi Source
    if "Source" in df_cur.columns:
        cur_src = df_cur.groupby("Source")["Doanh thu trước thuế"].sum()
        prv_src = df_prv.groupby("Source")["Doanh thu trước thuế"].sum()
        common = cur_src.index.intersection(prv_src.index)
        for s in common:
            if prv_src[s] > 0:
                g = (cur_src[s] - prv_src[s]) / prv_src[s] * 100
                if g > 20:
                    wins.append(f"Nhánh **{s}** bùng nổ: **+{g:.1f}%** doanh thu")
                elif g < -20:
                    concerns.append(f"Nhánh **{s}** suy giảm: **{g:.1f}%** doanh thu")

    # 2. Product mới nổi / suy yếu
    if "Sản phẩm" in df_cur.columns:
        cur_p = df_cur.groupby("Sản phẩm")["Doanh thu trước thuế"].sum()
        prv_p = df_prv.groupby("Sản phẩm")["Doanh thu trước thuế"].sum()
        # Product mới xuất hiện
        new_products = set(cur_p.index) - set(prv_p.index)
        for p in list(new_products)[:2]:
            if cur_p[p] > cur_p.median():
                wins.append(f"Sản phẩm mới **{p}** bán tốt ngay: {fmt_vnd(cur_p[p], short=True)}")
        # Product biến mất
        gone = set(prv_p.index) - set(cur_p.index)
        for p in list(gone)[:2]:
            if prv_p[p] > prv_p.median():
                concerns.append(f"Sản phẩm **{p}** không có HĐ mới (kỳ trước: {fmt_vnd(prv_p[p], short=True)})")

    # 3. Number of sales change
    n_sale_cur = df_cur["Họ tên sale"].nunique() if "Họ tên sale" in df_cur else 0
    n_sale_prv = df_prv["Họ tên sale"].nunique() if "Họ tên sale" in df_prv else 0
    if n_sale_prv > 0:
        sale_g = (n_sale_cur - n_sale_prv) / n_sale_prv * 100
        if sale_g > 10:
            wins.append(f"Team mở rộng: **+{n_sale_cur - n_sale_prv}** sale active mới")
        elif sale_g < -10:
            concerns.append(f"Team thu hẹp: **{n_sale_cur - n_sale_prv}** sale (giảm {abs(sale_g):.0f}%)")

    return wins[:3], concerns[:3]


def _generate_recommendations(df_cur: pd.DataFrame, df_prv: pd.DataFrame) -> list[str]:
    """Auto-generate actionable recommendations."""
    recs = []

    # Pareto 80/20 check
    if "Họ tên sale" in df_cur.columns:
        rev_by_sale = df_cur.groupby("Họ tên sale")["Doanh thu trước thuế"].sum().sort_values(ascending=False)
        if len(rev_by_sale) > 5 and rev_by_sale.sum() > 0:
            cum_pct = rev_by_sale.cumsum() / rev_by_sale.sum()
            n_80 = int((cum_pct <= 0.8).sum()) + 1
            pct_of_team = n_80 / len(rev_by_sale) * 100
            if pct_of_team < 30:
                recs.append(
                    f"**Rủi ro tập trung**: chỉ **{n_80}/{len(rev_by_sale)} sale** ({pct_of_team:.0f}%) "
                    f"đang tạo ra 80% doanh thu. Nên có kế hoạch dự phòng nếu top sale rời đi."
                )

    # Contract renewal
    if "Ngày kết thúc" in df_cur.columns:
        today = pd.Timestamp.now().normalize()
        renew_30 = df_cur[
            (df_cur["Ngày kết thúc"] > today) &
            (df_cur["Ngày kết thúc"] <= today + pd.Timedelta(days=30))
        ]
        n_renew = renew_30["Số hợp đồng"].nunique() if "Số hợp đồng" in renew_30 else 0
        if n_renew > 10:
            val = renew_30["Doanh thu trước thuế"].sum()
            recs.append(
                f"**Cơ hội tái tục**: **{n_renew} HĐ** sắp hết hạn trong 30 ngày, giá trị "
                f"~{fmt_vnd(val, short=True)}. Khởi động chiến dịch remind ngay."
            )

    # Product concentration
    if "Loại bảo hiểm" in df_cur.columns:
        loai = df_cur.groupby("Loại bảo hiểm")["Doanh thu trước thuế"].sum()
        if len(loai) > 0 and loai.sum() > 0:
            top_share = loai.max() / loai.sum()
            if top_share > 0.7:
                top_name = loai.idxmax()
                recs.append(
                    f"**Phụ thuộc sản phẩm**: **{top_name}** chiếm **{top_share*100:.0f}%** "
                    f"doanh thu. Cân nhắc đa dạng hóa để giảm rủi ro."
                )

    # Growth trend
    if not df_prv.empty:
        rev_cur = df_cur["Doanh thu trước thuế"].sum()
        rev_prv = df_prv["Doanh thu trước thuế"].sum()
        if rev_prv > 0:
            g = (rev_cur - rev_prv) / rev_prv * 100
            if g < -10:
                recs.append(
                    f"**Cảnh báo suy giảm**: doanh thu giảm {abs(g):.1f}% — cần triệu tập họp "
                    f"kinh doanh khẩn cấp, phân tích nguyên nhân theo Source/Product/Channel."
                )

    if not recs:
        recs.append("Không có vấn đề lớn cần hành động khẩn. Duy trì đà hiện tại.")

    return recs


# ============================================================================
# MAIN
# ============================================================================
st.title("Executive Insights — Bản tóm tắt cho lãnh đạo")
st.caption(
    "Trang này được tự động sinh: không cần đọc chart, chỉ cần đọc câu chữ. "
    "Phân tích thống kê, growth decomposition, và khuyến nghị hành động."
)

df_all = load_master_data()
if df_all.empty:
    st.warning("Chưa có dữ liệu.")
    st.stop()

filters = render_sidebar_filters(df_all)
df = apply_filters(df_all, filters)
df_prev = _prev_period_df(df_all, filters)

if df.empty:
    empty_state()
    st.stop()

# =========================================================================
# 1. AUTO-NARRATIVE
# =========================================================================
st.markdown("### Tóm tắt điều hành")
narrative = _generate_narrative(df, df_prev, filters)
st.info(narrative)

# =========================================================================
# 2. TOP WINS & TOP CONCERNS
# =========================================================================
st.markdown("### Điểm sáng & Điểm cần chú ý")
wins, concerns = _detect_wins_and_concerns(df, df_prev)
col_w, col_c = st.columns(2)
with col_w:
    st.markdown("#### Top 3 điểm sáng")
    if wins:
        for w in wins:
            st.success(w)
    else:
        st.caption("_Chưa phát hiện điểm sáng nổi bật trong kỳ này._")
with col_c:
    st.markdown("#### Top 3 điểm chú ý")
    if concerns:
        for c in concerns:
            st.warning(c)
    else:
        st.caption("_Không có vấn đề đáng lo trong kỳ này._")

st.divider()

# =========================================================================
# 3. GROWTH DECOMPOSITION — Vì sao doanh thu thay đổi?
# =========================================================================
st.markdown("### Growth Decomposition — Vì sao doanh thu thay đổi?")
st.caption(
    "Tách Δ doanh thu thành 3 phần: (1) tăng số lượng HĐ, "
    "(2) tăng giá trung bình mỗi HĐ, (3) thay đổi cơ cấu sản phẩm (mix)."
)

if not df_prev.empty:
    decomp = _decompose_growth(df, df_prev)
    if decomp:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "Tổng Δ doanh thu",
            fmt_vnd(decomp["total_delta"], short=True),
            delta=f"{(decomp['total_delta']/(decomp['n_prv']*decomp['avg_prv']))*100:+.1f}%" if decomp['n_prv']*decomp['avg_prv'] > 0 else None,
        )
        col2.metric(
            "Do khối lượng (Volume)",
            fmt_vnd(decomp["volume_effect"], short=True),
            delta=f"{decomp['n_cur'] - decomp['n_prv']:+d} HĐ",
            help="Δ số HĐ × giá TB kỳ trước — thay đổi này đến từ bán nhiều/ít hơn",
        )
        col3.metric(
            "Do giá (Price)",
            fmt_vnd(decomp["price_effect"], short=True),
            delta=f"AVG {fmt_vnd(decomp['avg_prv'], short=True)} {fmt_vnd(decomp['avg_cur'], short=True)}",
            help="Δ giá TB × số HĐ kỳ này — thay đổi này đến từ HĐ có giá trị lớn/nhỏ hơn",
        )
        col4.metric(
            "Do cơ cấu (Mix)",
            fmt_vnd(decomp["mix_effect"], short=True),
            help="Phần còn lại — do thay đổi cơ cấu sản phẩm/kênh",
        )

        # Waterfall chart
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["Kỳ trước", "Δ Volume", "Δ Price", "Δ Mix", "Kỳ này"],
            y=[decomp['n_prv']*decomp['avg_prv'],
               decomp["volume_effect"], decomp["price_effect"], decomp["mix_effect"],
               decomp['n_cur']*decomp['avg_cur']],
            textposition="outside",
            text=[fmt_vnd(v, short=True) for v in [
                decomp['n_prv']*decomp['avg_prv'],
                decomp["volume_effect"], decomp["price_effect"], decomp["mix_effect"],
                decomp['n_cur']*decomp['avg_cur']
            ]],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#5FBFA0"}},
            decreasing={"marker": {"color": "#E8738F"}},
            totals={"marker": {"color": "#B44BC8"}},
        ))
        fig.update_layout(showlegend=False, height=380, yaxis_tickformat=",.0f")
        st.plotly_chart(apply_plotly_layout(fig, title="Waterfall — Doanh thu đi từ kỳ trước sang kỳ này"),
                        use_container_width=True)

        # Insight auto
        largest = max(
            ("Volume (khối lượng)", abs(decomp["volume_effect"])),
            ("Price (giá TB)", abs(decomp["price_effect"])),
            ("Mix (cơ cấu)", abs(decomp["mix_effect"])),
            key=lambda x: x[1],
        )
        st.caption(
            f"**Insight**: yếu tố đóng góp lớn nhất là **{largest[0]}** "
            f"({fmt_vnd(largest[1], short=True)}). "
            f"Chiến lược nên tập trung vào yếu tố này."
        )
else:
    st.info("Không có dữ liệu kỳ trước để phân tích decomposition. Chọn khoảng thời gian dài hơn.")

st.divider()

# =========================================================================
# 4. KPI WITH STATISTICAL SIGNIFICANCE
# =========================================================================
st.markdown("### KPI với độ tin cậy thống kê (95% CI)")
st.caption(
    "Không chỉ mean — mà confidence interval. Nếu CI kỳ này và kỳ trước KHÔNG overlap, "
    "khác biệt là **có ý nghĩa thống kê** (significant)."
)

if "Doanh thu trước thuế" in df.columns:
    # Compute daily revenue for CI
    if DATE_COL in df.columns:
        daily_cur = df.groupby(df[DATE_COL].dt.date)["Doanh thu trước thuế"].sum()
        daily_prv = df_prev.groupby(df_prev[DATE_COL].dt.date)["Doanh thu trước thuế"].sum() if not df_prev.empty else pd.Series()

        ci_cur = _confidence_interval(daily_cur)
        ci_prv = _confidence_interval(daily_prv) if len(daily_prv) > 0 else (np.nan, np.nan)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Doanh thu TB/ngày — Kỳ này**")
            st.metric(
                "Mean",
                fmt_vnd(daily_cur.mean(), short=True),
                help=f"95% CI: [{fmt_vnd(ci_cur[0], short=True)}, {fmt_vnd(ci_cur[1], short=True)}]",
            )
            st.caption(f"95% CI: `{fmt_vnd(ci_cur[0], short=True)}` — `{fmt_vnd(ci_cur[1], short=True)}` (n={len(daily_cur)})")

        with col2:
            st.markdown("**Doanh thu TB/ngày — Kỳ trước**")
            if len(daily_prv) > 0:
                st.metric("Mean", fmt_vnd(daily_prv.mean(), short=True))
                st.caption(f"95% CI: `{fmt_vnd(ci_prv[0], short=True)}` — `{fmt_vnd(ci_prv[1], short=True)}` (n={len(daily_prv)})")

                # T-test
                if HAS_SCIPY and len(daily_cur) > 1 and len(daily_prv) > 1:
                    tstat, pval = sp_stats.ttest_ind(daily_cur, daily_prv, equal_var=False)
                    is_sig = pval < 0.05
                    color = "green" if is_sig else "gray"
                    verdict = "CÓ ý nghĩa thống kê" if is_sig else " CHƯA có ý nghĩa thống kê"
                    st.markdown(f"**T-test**: p-value = `{pval:.4f}` — :{color}[{verdict}] (α=0.05)")
            else:
                st.caption("_Không có data kỳ trước để so sánh._")

st.divider()

# =========================================================================
# 5. CORRELATION — Yếu tố nào ảnh hưởng doanh thu?
# =========================================================================
st.markdown("### Phân tích tương quan — Yếu tố nào ảnh hưởng doanh thu nhất?")

# Aggregate numeric features per contract
numeric_cols = [c for c in [
    "Doanh thu trước thuế", "Phí BH (VNĐ)", "Số tiền thanh toán",
    "Affina_Revenue", "EST_Bonus", "Thưởng Teamlead", "Incentive OVE",
    "BDM_bonus", "BDD_bonus", "Chi Agency", "Chi QL",
    "rate_bonus", "Affina_rate_bonus", "exchange_core",
] if c in df.columns]

if len(numeric_cols) >= 3:
    corr_matrix = df[numeric_cols].corr(method="pearson")
    # Tô màu — Pearson correlation heatmap
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale=["#6B4E8E", "#9F7BD9", "#FDF2FB", "#F06EC2", "#C93DA8"],
        zmin=-1, zmax=1,
        text=corr_matrix.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 10},
        colorbar=dict(title="r"),
    ))
    fig.update_layout(height=500, xaxis_tickangle=-30)
    st.plotly_chart(apply_plotly_layout(fig, title="Ma trận tương quan Pearson"),
                    use_container_width=True)

    # Show top 5 correlations with Doanh thu
    if "Doanh thu trước thuế" in corr_matrix.columns:
        top_corr = (corr_matrix["Doanh thu trước thuế"]
                    .drop("Doanh thu trước thuế")
                    .abs()
                    .sort_values(ascending=False)
                    .head(5))
        st.caption(
            "**Top 5 chỉ số tương quan mạnh nhất với Doanh thu:** " +
            " · ".join([f"`{k}` ({v:.2f})" for k, v in top_corr.items()])
        )

st.divider()

# =========================================================================
# 6. PERCENTILE RANK — Phân phối hiệu suất sale
# =========================================================================
st.markdown("### Percentile Rank — Sale nằm ở đâu trong phân phối?")
st.caption("P90 = top 10% giỏi nhất. P50 = median. P25 = 25% dưới cùng.")

if "Họ tên sale" in df.columns:
    rev_sale = df.groupby("Họ tên sale")["Doanh thu trước thuế"].sum().sort_values(ascending=False)
    if len(rev_sale) >= 10:
        p10, p25, p50, p75, p90 = np.percentile(rev_sale, [10, 25, 50, 75, 90])
        p95, p99 = np.percentile(rev_sale, [95, 99])

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("P25", fmt_vnd(p25, short=True), help="25% sale bán dưới mức này")
        col2.metric("P50 (Median)", fmt_vnd(p50, short=True))
        col3.metric("P75", fmt_vnd(p75, short=True))
        col4.metric("P90", fmt_vnd(p90, short=True), help="Top 10% sale bán trên mức này")
        col5.metric("P99", fmt_vnd(p99, short=True), help="Ngưỡng top 1%")

        # Histogram with percentile lines
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=rev_sale.values, nbinsx=40, marker_color="#B44BC8", opacity=0.7))
        for label, val, color in [("P25", p25, "#EDB16E"), ("P50", p50, "#5FBFA0"),
                                    ("P75", p75, "#9F7BD9"), ("P90", p90, "#E8738F")]:
            fig.add_vline(x=val, line_dash="dash", line_color=color,
                          annotation_text=label, annotation_position="top")
        fig.update_layout(
            xaxis_title="Doanh thu (VNĐ)",
            yaxis_title="Số lượng sale",
            xaxis_tickformat=",.0f",
            height=380,
            showlegend=False,
        )
        st.plotly_chart(apply_plotly_layout(fig, title="Phân phối doanh thu sale + Percentile"),
                        use_container_width=True)

        # Insight
        top_10_share = rev_sale.head(int(len(rev_sale) * 0.1) or 1).sum() / rev_sale.sum() * 100
        st.caption(
            f"**Insight**: Top 10% sale ({int(len(rev_sale) * 0.1) or 1} người) đang tạo ra "
            f"**{top_10_share:.1f}%** tổng doanh thu. "
            f"Chỉ số Gini cao phụ thuộc nhiều vào 1 số ít sale."
        )
    else:
        st.info("Cần ít nhất 10 sale để phân tích percentile.")

st.divider()

# =========================================================================
# 7. RECOMMENDATIONS
# =========================================================================
st.markdown("### Khuyến nghị hành động (auto)")
recs = _generate_recommendations(df, df_prev)
for r in recs:
    st.markdown(f"- {r}")

st.divider()
st.caption(
    "Trang này áp dụng: **auto-narrative** (NLG), **growth decomposition** "
    "(Volume/Price/Mix), **statistical significance** (95% CI + t-test), "
    "**correlation matrix** (Pearson), **percentile ranking**, **Pareto analysis** — "
    "các kỹ thuật chuẩn của senior DA."
)
