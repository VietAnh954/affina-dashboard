"""
================================================================================
 TRANG 9 — FORECAST & ANOMALY DETECTION (Predictive Analytics)
================================================================================
Trả lời:
  1. Tháng tới doanh thu bao nhiêu? (forecast 30 ngày)
  2. Có ngày nào bất thường không? (anomaly detection)
  3. Có mùa vụ không? (seasonality decomposition)
  4. Thứ mấy trong tuần bán tốt nhất? (day-of-week pattern)
  5. Doanh thu dao động ổn định hay biến động cao? (volatility)

Kỹ thuật DA áp dụng:
  • Time-series forecast (Exponential Smoothing / Holt-Winters)
  • Anomaly detection (Z-score + IQR method)
  • Seasonal decomposition (trend + seasonal + residual)
  • Growth rate volatility (rolling std)
  • Day-of-week & Month-of-year heatmap
================================================================================
"""
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

st.set_page_config(page_title="Forecast & Anomaly", layout="wide")

from lib.auth import require_auth
require_auth("forecast", "Forecast & Anomaly")


# Try import statsmodels
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.seasonal import seasonal_decompose
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


# ============================================================================
# HELPERS
# ============================================================================
def _prep_daily_series(df: pd.DataFrame, metric_col: str = "Doanh thu trước thuế") -> pd.Series:
    """Tổng hợp doanh thu theo ngày, fill 0 cho ngày không có HĐ."""
    if DATE_COL not in df.columns or metric_col not in df.columns:
        return pd.Series(dtype=float)
    daily = df.groupby(df[DATE_COL].dt.date)[metric_col].sum()
    daily.index = pd.to_datetime(daily.index)
    # Fill missing days với 0
    if len(daily) > 1:
        full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
        daily = daily.reindex(full_range, fill_value=0)
    return daily.sort_index()


def _forecast_holtwinters(series: pd.Series, periods: int = 30) -> tuple:
    """Forecast bằng Holt-Winters với additive seasonality (weekly)."""
    if not HAS_STATSMODELS or len(series) < 30:
        return None, None, None

    # Fill 0 với small value để tránh log(0) nếu multiplicative
    y = series.copy()
    try:
        # Weekly seasonality (7 days)
        if len(y) >= 21:
            model = ExponentialSmoothing(y, trend="add", seasonal="add", seasonal_periods=7).fit()
        else:
            model = ExponentialSmoothing(y, trend="add", seasonal=None).fit()
        forecast = model.forecast(periods)
        # Simple CI dựa trên residuals
        resid = model.resid
        std = resid.std()
        upper = forecast + 1.96 * std
        lower = forecast - 1.96 * std
        return forecast, lower.clip(lower=0), upper
    except Exception as e:
        st.warning(f"Không thể forecast: {e}")
        return None, None, None


def _detect_anomalies(series: pd.Series, method: str = "zscore", threshold: float = 2.5) -> pd.Series:
    """Trả về boolean series — True = anomaly."""
    if method == "zscore":
        z = np.abs((series - series.mean()) / series.std())
        return z > threshold
    elif method == "iqr":
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        return (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
    return pd.Series(False, index=series.index)


# ============================================================================
# MAIN
# ============================================================================
st.title("Forecast & Anomaly Detection")
st.caption(
    "Dự báo doanh thu tương lai, phát hiện ngày bất thường, "
    "và phân tích mùa vụ — 3 công cụ predictive analytics thiết yếu."
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

# ==========================================================================
# 1. TIME-SERIES FORECAST
# ==========================================================================
st.markdown("### Dự báo doanh thu 30 ngày tới")

if not HAS_STATSMODELS:
    st.warning(
        "Thiếu thư viện `statsmodels`. Thêm vào `requirements.txt` và deploy lại. "
        "Chart bên dưới sẽ chỉ hiển thị lịch sử."
    )

series = _prep_daily_series(df)
if len(series) >= 30:
    # Forecast
    forecast, lower, upper = _forecast_holtwinters(series, periods=30)

    fig = go.Figure()

    # Historical
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines", name="Doanh thu thực tế",
        line=dict(color="#B44BC8", width=2),
    ))

    # Rolling 7-day average
    ma7 = series.rolling(7).mean()
    fig.add_trace(go.Scatter(
        x=ma7.index, y=ma7.values,
        mode="lines", name="MA 7 ngày",
        line=dict(color="#EDB16E", width=1, dash="dot"),
    ))

    if forecast is not None:
        # Forecast
        fig.add_trace(go.Scatter(
            x=forecast.index, y=forecast.values,
            mode="lines", name="Dự báo",
            line=dict(color="#E8738F", width=2, dash="dash"),
        ))
        # Confidence band
        fig.add_trace(go.Scatter(
            x=upper.index, y=upper.values,
            mode="lines", line=dict(width=0),
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=lower.index, y=lower.values,
            mode="lines", line=dict(width=0),
            fillcolor="rgba(239, 68, 68, 0.2)",
            fill="tonexty", name="95% CI (dự báo)",
        ))

    fig.update_layout(
        xaxis_title="Ngày",
        yaxis_title="Doanh thu (VNĐ)",
        yaxis_tickformat=",.0f",
        hovermode="x unified",
        height=450,
    )
    st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

    # Summary metrics
    if forecast is not None:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Trung bình 30 ngày qua",
            fmt_vnd(series.tail(30).mean(), short=True),
        )
        c2.metric(
            "Trung bình 30 ngày tới (dự báo)",
            fmt_vnd(forecast.mean(), short=True),
            delta=fmt_pct((forecast.mean() - series.tail(30).mean()) / series.tail(30).mean())
                  if series.tail(30).mean() > 0 else None,
        )
        c3.metric(
            "Tổng dự báo 30 ngày",
            fmt_vnd(forecast.sum(), short=True),
        )
        c4.metric(
            "Độ dao động ±",
            fmt_vnd((upper - lower).mean() / 2, short=True),
            help="Độ rộng confidence interval trung bình",
        )

        st.caption(
            f"**Model dùng:** Holt-Winters Exponential Smoothing (additive trend + weekly seasonality). "
            f"**Base data:** {len(series)} ngày lịch sử. "
            f"**Warning:** dự báo chỉ tin cậy nếu pattern quá khứ tiếp tục — sự kiện bất ngờ (chương trình mới, "
            f"khủng hoảng) sẽ khiến sai lệch."
        )
else:
    st.info(f"Cần ít nhất 30 ngày data. Hiện có {len(series)} ngày. Nới thời gian filter.")

st.divider()

# ==========================================================================
# 2. ANOMALY DETECTION
# ==========================================================================
st.markdown("### Anomaly Detection — Ngày nào bất thường?")

col_setting1, col_setting2 = st.columns(2)
method = col_setting1.radio(
    "Phương pháp:",
    options=["zscore", "iqr"],
    format_func=lambda x: {"zscore": "Z-score (mặc định)", "iqr": "IQR (Interquartile Range)"}[x],
    horizontal=True,
    key="anom_method",
)
threshold = col_setting2.slider(
    "Ngưỡng (Z-score threshold):",
    min_value=1.5, max_value=4.0, value=2.5, step=0.1,
    disabled=(method == "iqr"),
) if method == "zscore" else 2.5

if len(series) >= 10:
    anomalies = _detect_anomalies(series, method=method, threshold=threshold)
    n_anom = anomalies.sum()

    fig = go.Figure()
    # Normal points
    normal_series = series[~anomalies]
    fig.add_trace(go.Scatter(
        x=normal_series.index, y=normal_series.values,
        mode="markers+lines",
        line=dict(color="#B44BC8", width=1),
        marker=dict(size=5, color="#B44BC8"),
        name="Bình thường",
    ))
    # Anomalies
    anom_series = series[anomalies]
    if not anom_series.empty:
        fig.add_trace(go.Scatter(
            x=anom_series.index, y=anom_series.values,
            mode="markers",
            marker=dict(size=12, color="#E8738F", symbol="star", line=dict(width=1, color="black")),
            name=f"Bất thường ({n_anom})",
        ))

    # Mean ± threshold lines
    mean_val = series.mean()
    std_val = series.std()
    fig.add_hline(y=mean_val, line_dash="dot", line_color="green",
                  annotation_text=f"Mean: {fmt_vnd(mean_val, short=True)}")
    if method == "zscore":
        fig.add_hline(y=mean_val + threshold * std_val, line_dash="dash", line_color="red",
                      annotation_text=f"+{threshold}σ")
        fig.add_hline(y=max(0, mean_val - threshold * std_val), line_dash="dash", line_color="red",
                      annotation_text=f"-{threshold}σ")

    fig.update_layout(
        xaxis_title="Ngày",
        yaxis_title="Doanh thu (VNĐ)",
        yaxis_tickformat=",.0f",
        hovermode="x unified",
        height=400,
    )
    st.plotly_chart(apply_plotly_layout(fig, title=f"Phát hiện {n_anom} ngày bất thường"),
                    use_container_width=True)

    # Table các ngày anomaly
    if n_anom > 0:
        anom_df = pd.DataFrame({
            "Ngày": anom_series.index.strftime("%d/%m/%Y (%A)"),
            "Doanh thu": [fmt_vnd(v, short=True) for v in anom_series.values],
            "Z-score": [(v - mean_val) / std_val for v in anom_series.values],
        })
        anom_df["Loại"] = anom_df["Z-score"].apply(lambda z: "Đột biến CAO" if z > 0 else "Sụt giảm SÂU")
        anom_df["Z-score"] = anom_df["Z-score"].apply(lambda z: f"{z:+.2f}σ")
        anom_df = anom_df.sort_values("Ngày", ascending=False)

        st.markdown("** Chi tiết các ngày bất thường:**")
        st.dataframe(anom_df, hide_index=True, use_container_width=True)

        st.caption(
            "**Cách dùng:** Kiểm tra ngày bất thường — có sự kiện gì đặc biệt "
            "(chương trình khuyến mãi, holiday, sự cố hệ thống)? "
            "Ngày CAO bất thường nhân rộng cách làm. "
            "Ngày THẤP bất thường điều tra nguyên nhân."
        )
    else:
        st.success(f"Không có ngày nào bất thường (ngưỡng ±{threshold}σ). Doanh thu ổn định.")

st.divider()

# ==========================================================================
# 3. SEASONALITY DECOMPOSITION
# ==========================================================================
st.markdown("### Seasonal Decomposition — Xu hướng / Mùa vụ / Nhiễu")
st.caption(
    "Tách chuỗi time-series thành 3 thành phần: **Trend** (xu hướng dài hạn), "
    "**Seasonal** (mùa vụ tuần), **Residual** (biến động ngẫu nhiên)."
)

if HAS_STATSMODELS and len(series) >= 28:
    try:
        # Weekly seasonality
        decomp = seasonal_decompose(series, model="additive", period=7, extrapolate_trend="freq")

        fig = go.Figure()
        fig = go.Figure(data=[
            go.Scatter(x=series.index, y=series.values, name="Observed", line=dict(color="#B44BC8")),
        ])
        st.markdown("**1⃣ Observed** — chuỗi gốc")
        st.line_chart(pd.DataFrame({"Observed": series}), height=200)

        st.markdown("**2⃣ Trend** — xu hướng dài hạn (làm mịn)")
        st.line_chart(pd.DataFrame({"Trend": decomp.trend.dropna()}), height=200)

        col_s, col_r = st.columns(2)
        with col_s:
            st.markdown("**3⃣ Seasonal** — mùa vụ tuần")
            # Chỉ show 4 tuần đầu để rõ pattern
            seasonal_show = decomp.seasonal.head(28)
            st.line_chart(pd.DataFrame({"Seasonal": seasonal_show}), height=200)

        with col_r:
            st.markdown("**4⃣ Residual** — biến động ngẫu nhiên")
            st.line_chart(pd.DataFrame({"Residual": decomp.resid.dropna()}), height=200)

        # Insights
        seasonal_range = decomp.seasonal.max() - decomp.seasonal.min()
        trend_change = decomp.trend.dropna().iloc[-1] - decomp.trend.dropna().iloc[0]

        col1, col2, col3 = st.columns(3)
        col1.metric("Trend change (tổng kỳ)", fmt_vnd(trend_change, short=True))
        col2.metric("Biên độ mùa vụ (tuần)", fmt_vnd(seasonal_range, short=True))
        col3.metric("Std residual", fmt_vnd(decomp.resid.dropna().std(), short=True))
    except Exception as e:
        st.warning(f"Không thể decompose: {e}")
else:
    st.info(f"Cần ít nhất 28 ngày (4 tuần) và thư viện `statsmodels`. Hiện có {len(series)} ngày.")

st.divider()

# ==========================================================================
# 4. DAY-OF-WEEK & MONTH-OF-YEAR PATTERN
# ==========================================================================
st.markdown("### Pattern theo Thứ trong tuần × Tháng trong năm")

if DATE_COL in df.columns:
    df_time = df.copy()
    df_time["dow"] = df_time[DATE_COL].dt.day_name()
    df_time["month"] = df_time[DATE_COL].dt.month
    df_time["month_name"] = df_time[DATE_COL].dt.strftime("%m/%Y")

    # Vietnam-friendly day names
    dow_map = {
        "Monday": "T2", "Tuesday": "T3", "Wednesday": "T4",
        "Thursday": "T5", "Friday": "T6", "Saturday": "T7", "Sunday": "CN",
    }
    df_time["dow_vn"] = df_time["dow"].map(dow_map)
    dow_order = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("** Doanh thu theo Thứ trong tuần**")
        dow_stats = df_time.groupby("dow_vn")["Doanh thu trước thuế"].agg(["sum", "mean", "count"])
        dow_stats = dow_stats.reindex(dow_order)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dow_stats.index, y=dow_stats["sum"],
            name="Tổng doanh thu",
            marker_color="#B44BC8",
            text=[fmt_vnd(v, short=True) for v in dow_stats["sum"]],
            textposition="outside",
        ))
        fig.update_layout(
            yaxis_tickformat=",.0f",
            xaxis_title="Thứ",
            yaxis_title="Doanh thu",
            height=350,
            showlegend=False,
        )
        st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

        # Best/worst day
        if dow_stats["sum"].notna().any():
            best_day = dow_stats["sum"].idxmax()
            worst_day = dow_stats["sum"].idxmin()
            best_avg = dow_stats.loc[best_day, "mean"]
            worst_avg = dow_stats.loc[worst_day, "mean"]
            if worst_avg > 0:
                ratio = best_avg / worst_avg
                st.caption(
                    f"**{best_day}** là ngày mạnh nhất (TB {fmt_vnd(best_avg, short=True)}/ngày). "
                    f"Cao gấp **{ratio:.1f}x** so với **{worst_day}** ({fmt_vnd(worst_avg, short=True)}/ngày)."
                )

    with col2:
        st.markdown("** Doanh thu theo tháng trong năm**")
        if len(df_time) > 0:
            month_stats = df_time.groupby(df_time[DATE_COL].dt.month)["Doanh thu trước thuế"].sum()
            month_names = ["Tháng " + str(m) for m in month_stats.index]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=month_names, y=month_stats.values,
                marker_color="#5FBFA0",
                text=[fmt_vnd(v, short=True) for v in month_stats.values],
                textposition="outside",
            ))
            fig.update_layout(
                yaxis_tickformat=",.0f",
                xaxis_title="Tháng",
                yaxis_title="Doanh thu",
                height=350,
                showlegend=False,
            )
            st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

    # Heatmap DoW × Week of year
    st.markdown("** Heatmap: Thứ × Tuần trong năm**")
    df_time["woy"] = df_time[DATE_COL].dt.isocalendar().week
    df_time["year"] = df_time[DATE_COL].dt.year
    df_time["year_woy"] = df_time["year"].astype(str) + "-W" + df_time["woy"].astype(str).str.zfill(2)

    heat = df_time.pivot_table(
        index="dow_vn", columns="year_woy",
        values="Doanh thu trước thuế", aggfunc="sum", fill_value=0,
    )
    heat = heat.reindex(dow_order)

    # Limit columns nếu quá nhiều
    if heat.shape[1] > 52:
        heat = heat.iloc[:, -52:]

    fig = px.imshow(
        heat, aspect="auto",
        color_continuous_scale=["#FDF2FB", "#F2C4E8", "#E085D0", "#C95BBE", "#8E2F7A"],
        labels=dict(x="Tuần trong năm", y="Thứ", color="Doanh thu"),
    )
    fig.update_layout(height=280)
    st.plotly_chart(apply_plotly_layout(fig, title=""), use_container_width=True)

st.divider()

# ==========================================================================
# 5. VOLATILITY ANALYSIS
# ==========================================================================
st.markdown("### Volatility — Doanh thu ổn định hay biến động?")

if len(series) >= 14:
    # Coefficient of Variation trên rolling 30 days
    rolling_mean = series.rolling(30).mean()
    rolling_std = series.rolling(30).std()
    cv = (rolling_std / rolling_mean).dropna() * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cv.index, y=cv.values,
        fill="tozeroy",
        line=dict(color="#E8738F"),
        name="CoV %",
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="orange",
                  annotation_text="Ngưỡng biến động cao (50%)")
    fig.update_layout(
        yaxis_title="CoV (%)",
        xaxis_title="Ngày",
        height=280,
    )
    st.plotly_chart(apply_plotly_layout(fig, title="Coefficient of Variation (rolling 30 ngày)"),
                    use_container_width=True)

    current_cv = cv.iloc[-1] if len(cv) > 0 else np.nan
    avg_cv = cv.mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("CoV hiện tại", f"{current_cv:.1f}%" if not pd.isna(current_cv) else "-")
    col2.metric("CoV trung bình", f"{avg_cv:.1f}%")
    col3.metric("CoV cao nhất kỳ", f"{cv.max():.1f}%")

    if not pd.isna(current_cv):
        if current_cv < 30:
            st.success(f"Doanh thu **ỔN ĐỊNH** (CoV = {current_cv:.1f}% < 30%). Dễ dự báo & lập kế hoạch.")
        elif current_cv < 60:
            st.info(f"Doanh thu **BIẾN ĐỘNG TRUNG BÌNH** (CoV = {current_cv:.1f}%).")
        else:
            st.warning(
                f"Doanh thu **BIẾN ĐỘNG CAO** (CoV = {current_cv:.1f}% > 60%). "
                f"Khó dự báo — cần điều tra: sự phụ thuộc vào chương trình khuyến mãi, deal lớn không thường xuyên?"
            )

st.divider()
st.caption(
    "Trang này áp dụng: **Exponential Smoothing** (Holt-Winters) forecast, "
    "**Z-score & IQR** anomaly detection, **STL/Seasonal decomposition**, "
    "**Coefficient of Variation** volatility — chuẩn time-series analytics."
)
