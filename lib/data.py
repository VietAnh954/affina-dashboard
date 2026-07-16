"""
lib/data.py — Shared utilities cho toàn bộ Streamlit dashboard

- Kết nối Supabase (cached engine)
- Load dashboard_master_data (cache TTL 5 phút)
- Load dashboard_meta (last update info)
- Helper format số VNĐ, ngày
- Global filter application
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# ============================================================================
# Constants
# ============================================================================
COLORS = {
    # ── AFFINA BRAND PALETTE (hồng pastel) ──────────────────────────────
    # Trích xuất từ logo (#F850F8) + footer gradient (#7038A0 → #D078E0)
    # 3 Source dùng 3 sắc độ chính của brand — phân biệt rõ nhưng hài hòa
    "Core": "#B44BC8",        # tím orchid — nhánh chủ lực, đậm nhất
    "Neo":  "#F06EC2",        # hồng flamingo — nổi bật thứ 2
    "TSA":  "#8B6FC9",        # tím lavender — dịu

    "positive": "#5FBFA0",    # xanh mint pastel (tăng trưởng)
    "negative": "#E8738F",    # hồng rose đậm (suy giảm)
    "warning":  "#EDB16E",    # cam peach pastel

    # 7 Loại bảo hiểm — gradient hồng→tím quanh brand hue
    "BHSK":      "#E85BD8",   # hồng magenta (sản phẩm chủ lực = màu logo)
    "BHXM":      "#9F7BD9",   # tím lilac
    "BHYT/BHXH": "#C77BC9",   # hồng cẩm quỳ
    "BHOTO":     "#7D5BA6",   # tím đậm
    "BHDL":      "#F2A0DC",   # hồng phấn nhạt
    "TNDS":      "#6B4E8E",   # tím than
    "BHRR":      "#D96FA8",   # hồng dâu
}

# Gradient scale cho heatmap/treemap — thay Blues/YlOrRd mặc định
PINK_SCALE = ["#FDF2FB", "#F9D8F0", "#F0AEE2", "#E285D3", "#C95BBE", "#A6409E", "#7D2E78"]

DATE_COL = "Ngày thanh toán"
DEFAULT_TTL = 300 # 5 phút


# ============================================================================
# Connection
# ============================================================================
def _get_db_uri() -> str:
    # Priority: st.secrets env var
    try:
        return st.secrets["SUPABASE_DB_URI"]
    except Exception:
        uri = os.environ.get("SUPABASE_DB_URI")
        if not uri:
            st.error("Thiếu `SUPABASE_DB_URI` trong secrets hoặc env")
            st.stop()
        return uri


@st.cache_resource
def get_engine():
    return create_engine(_get_db_uri(), pool_pre_ping=True)


# ============================================================================
# Data loading
# ============================================================================
@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Đang tải data từ Supabase...")
def load_master_data() -> pd.DataFrame:
    """Đọc dashboard_master_data. Cache 5 phút."""
    engine = get_engine()
    try:
        df = pd.read_sql(text('SELECT * FROM dashboard_master_data'), engine)
    except Exception as e:
        st.error(f"Không đọc được bảng dashboard_master_data: {e}")
        st.info("Có thể job GitHub Actions chưa chạy lần đầu. "
                "Vào GitHub Actions Build Dashboard Data Run workflow.")
        st.stop()

    if DATE_COL in df.columns:
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    for c in ["Ngày bắt đầu", "Ngày kết thúc", "Ngày sinh NĐBH", "Ngày sinh NMBH"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


@st.cache_data(ttl=DEFAULT_TTL)
def load_meta() -> dict:
    """Đọc dashboard_meta để hiển thị thông tin update mới nhất."""
    engine = get_engine()
    try:
        row = pd.read_sql(text(
            "SELECT * FROM dashboard_meta ORDER BY id DESC LIMIT 1"
        ), engine)
        return row.iloc[0].to_dict() if not row.empty else {}
    except Exception:
        return {}


# ============================================================================
# Global sidebar filters
# ============================================================================
def render_sidebar_filters(df: pd.DataFrame) -> dict:
    """
    Render sidebar filters. Return dict of applied filters.
    Sidebar hiển thị chung cho mọi trang import và gọi từ mọi page.
    """
    st.sidebar.markdown("### Bộ lọc chung")

    # Date range
    date_min = df[DATE_COL].min()
    date_max = df[DATE_COL].max()
    if pd.isna(date_min):
        date_min = pd.Timestamp("2024-01-01")
    if pd.isna(date_max):
        date_max = pd.Timestamp.today()

    date_range = st.sidebar.date_input(
        "Khoảng thời gian",
        value=(date_min.date(), date_max.date()),
        min_value=date_min.date(),
        max_value=date_max.date(),
        format="DD/MM/YYYY",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date_min.date(), date_max.date()

    # Source
    sources = sorted(df["Source"].dropna().unique().tolist()) if "Source" in df.columns else []
    selected_sources = st.sidebar.multiselect(
        "Source", options=sources, default=sources
    )

    # Channel
    channels = sorted(df["Channel"].dropna().unique().tolist()) if "Channel" in df.columns else []
    selected_channels = st.sidebar.multiselect(
        "Channel", options=channels, default=channels
    )

    # Loại BH
    loai_bh = sorted(df["Loại bảo hiểm"].dropna().unique().tolist()) if "Loại bảo hiểm" in df.columns else []
    selected_loai = st.sidebar.multiselect(
        "Loại bảo hiểm", options=loai_bh, default=loai_bh
    )

    # Nhà BH
    nha_bh = sorted(df["Nhà BH"].dropna().unique().tolist()) if "Nhà BH" in df.columns else []
    selected_nha = st.sidebar.multiselect(
        "Nhà bảo hiểm", options=nha_bh, default=[] # default trống không lọc
    )

    st.sidebar.divider()

    # Refresh button
    if st.sidebar.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()

    # Meta info
    meta = load_meta()
    if meta:
        updated_at = meta.get("updated_at")
        if updated_at is not None:
            # Convert to VN timezone
            if isinstance(updated_at, str):
                updated_at = pd.to_datetime(updated_at)
            if updated_at.tzinfo is None:
                updated_at = updated_at.tz_localize("UTC")
            vn_time = updated_at.astimezone(timezone(timedelta(hours=7)))
            st.sidebar.caption(f"Cập nhật gần nhất:\n**{vn_time.strftime('%d/%m/%Y %H:%M')}** (VN)")
        st.sidebar.caption(f"Rows: **{meta.get('row_count', 0):,}**")
        st.sidebar.caption(f"Build: {meta.get('duration_sec', 0)}s")

    st.sidebar.divider()
    st.sidebar.caption("Made with for Affina")

    return {
        "start_date": pd.Timestamp(start_date),
        "end_date": pd.Timestamp(end_date),
        "sources": selected_sources,
        "channels": selected_channels,
        "loai_bh": selected_loai,
        "nha_bh": selected_nha,
    }


def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """Apply filter dict lên dataframe."""
    m = pd.Series(True, index=df.index)
    if DATE_COL in df.columns:
        m &= (df[DATE_COL] >= f["start_date"]) & (df[DATE_COL] <= f["end_date"] + pd.Timedelta(days=1))
    if f["sources"] and "Source" in df.columns:
        m &= df["Source"].isin(f["sources"])
    if f["channels"] and "Channel" in df.columns:
        m &= df["Channel"].isin(f["channels"])
    if f["loai_bh"] and "Loại bảo hiểm" in df.columns:
        m &= df["Loại bảo hiểm"].isin(f["loai_bh"])
    if f["nha_bh"] and "Nhà BH" in df.columns:
        m &= df["Nhà BH"].isin(f["nha_bh"])
    return df[m].copy()


# ============================================================================
# Formatting helpers
# ============================================================================
def fmt_vnd(x, short: bool = False) -> str:
    if pd.isna(x):
        return "-"
    x = float(x)
    if short:
        for unit, div in [("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)]:
            if abs(x) >= div:
                return f"{x/div:,.2f}{unit} ₫"
        return f"{x:,.0f} ₫"
    return f"{x:,.0f} ₫"


def fmt_pct(x) -> str:
    if pd.isna(x):
        return "-"
    return f"{x*100:.1f}%"


def fmt_num(x) -> str:
    if pd.isna(x):
        return "-"
    return f"{int(x):,}"


def apply_plotly_layout(fig, title: str = "", height: int | None = None):
    fig.update_layout(
        title=title,
        template="plotly_white",
        font=dict(family="Segoe UI, Arial", size=12),
        margin=dict(l=30, r=20, t=50 if title else 20, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(font_size=13, bgcolor="white", bordercolor="#E85BD8"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFAFE",
        colorway=[
            "#E85BD8", "#B44BC8", "#8B6FC9", "#F06EC2", "#7D5BA6",
            "#D96FA8", "#C77BC9", "#9F7BD9", "#F2A0DC", "#6B4E8E",
        ],
    )
    if height:
        fig.update_layout(height=height)
    return fig


def empty_state(msg: str = "Không có dữ liệu phù hợp với bộ lọc hiện tại."):
    st.info(msg)
