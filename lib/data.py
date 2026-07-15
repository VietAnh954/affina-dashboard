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
    "Core": "#1F77B4",
    "Neo":  "#FF7F0E",
    "TSA":  "#2CA02C",
    "positive": "#2CA02C",
    "negative": "#D62728",
    "warning": "#F1C40F",
    # Loại bảo hiểm
    "BHSK":      "#E74C3C",
    "BHXM":      "#3498DB",
    "BHYT/BHXH": "#9B59B6",
    "BHOTO":     "#F39C12",
    "BHDL":      "#1ABC9C",
    "TNDS":      "#34495E",
    "BHRR":      "#E67E22",
}

DATE_COL = "Ngày thanh toán"
DEFAULT_TTL = 300  # 5 phút


# ============================================================================
# Connection
# ============================================================================
def _get_db_uri() -> str:
    # Priority: st.secrets → env var
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
                "Vào GitHub → Actions → Build Dashboard Data → Run workflow.")
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
    Persist state across pages and apply cascade filtering.
    """
    st.sidebar.markdown("### Bộ lọc chung")

    # Date range
    date_min = df[DATE_COL].min()
    date_max = df[DATE_COL].max()
    if pd.isna(date_min):
        date_min = pd.Timestamp("2024-01-01")
    if pd.isna(date_max):
        date_max = pd.Timestamp.today()

    if "f_date" not in st.session_state:
        st.session_state["f_date"] = (date_min.date(), date_max.date())
    
    # Ensure value fits min/max (in case data changes)
    val_date = st.session_state["f_date"]
    if isinstance(val_date, tuple) and len(val_date) == 2:
        val_start = max(date_min.date(), min(date_max.date(), val_date[0]))
        val_end = max(date_min.date(), min(date_max.date(), val_date[1]))
        st.session_state["f_date"] = (val_start, val_end)

    date_range = st.sidebar.date_input(
        "Khoảng thời gian",
        value=st.session_state["f_date"],
        min_value=date_min.date(),
        max_value=date_max.date(),
        format="DD/MM/YYYY",
        key="f_date",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date_min.date(), date_max.date()

    # --- CASCADE FILTERING & PERSISTENCE ---

    # 1. Source (Base filter)
    sources = sorted(df["Source"].dropna().unique().tolist()) if "Source" in df.columns else []
    if "f_source" not in st.session_state:
        st.session_state["f_source"] = sources
    else:
        st.session_state["f_source"] = [s for s in st.session_state["f_source"] if s in sources]

    selected_sources = st.sidebar.multiselect(
        "Source", options=sources,
        key="f_source",
    )

    # 2. Channel (Depends on Source)
    if selected_sources:
        df_c = df[df["Source"].isin(selected_sources)]
    else:
        df_c = df
    channels = sorted(df_c["Channel"].dropna().unique().tolist()) if "Channel" in df_c.columns else []
    if "f_channel" not in st.session_state:
        st.session_state["f_channel"] = channels
    else:
        st.session_state["f_channel"] = [c for c in st.session_state["f_channel"] if c in channels]

    selected_channels = st.sidebar.multiselect(
        "Channel", options=channels,
        key="f_channel",
    )

    # 3. Loại bảo hiểm (Depends on Source & Channel)
    df_l = df_c
    if selected_channels:
        df_l = df_l[df_l["Channel"].isin(selected_channels)]
    loai_bh = sorted(df_l["Loại bảo hiểm"].dropna().unique().tolist()) if "Loại bảo hiểm" in df_l.columns else []
    if "f_loai_bh" not in st.session_state:
        st.session_state["f_loai_bh"] = loai_bh
    else:
        st.session_state["f_loai_bh"] = [l for l in st.session_state["f_loai_bh"] if l in loai_bh]

    selected_loai = st.sidebar.multiselect(
        "Loại bảo hiểm", options=loai_bh,
        key="f_loai_bh",
    )

    # 4. Nhà bảo hiểm (Depends on Source & Channel & Loại BH)
    df_n = df_l
    if selected_loai:
        df_n = df_n[df_n["Loại bảo hiểm"].isin(selected_loai)]
    nha_bh = sorted(df_n["Nhà BH"].dropna().unique().tolist()) if "Nhà BH" in df_n.columns else []
    if "f_nha_bh" not in st.session_state:
        st.session_state["f_nha_bh"] = []  # Default empty
    else:
        st.session_state["f_nha_bh"] = [n for n in st.session_state["f_nha_bh"] if n in nha_bh]

    selected_nha = st.sidebar.multiselect(
        "Nhà bảo hiểm", options=nha_bh,
        key="f_nha_bh",
    )

    st.sidebar.divider()

    # Reset Filters Button (Priority 3 Improvement #9)
    if st.sidebar.button("Reset Filters", use_container_width=True):
        st.session_state["f_date"] = (date_min.date(), date_max.date())
        st.session_state["f_source"] = sources
        st.session_state["f_channel"] = sorted(df["Channel"].dropna().unique().tolist()) if "Channel" in df.columns else []
        st.session_state["f_loai_bh"] = sorted(df["Loại bảo hiểm"].dropna().unique().tolist()) if "Loại bảo hiểm" in df.columns else []
        st.session_state["f_nha_bh"] = []
        st.rerun()

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
    st.sidebar.caption("Made for Affina")

    return {
        "start_date": pd.Timestamp(start_date),
        "end_date":   pd.Timestamp(end_date),
        "sources":    selected_sources,
        "channels":   selected_channels,
        "loai_bh":    selected_loai,
        "nha_bh":     selected_nha,
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
        if abs(x) >= 1e12: return f"{x/1e12:,.2f} nghìn tỷ"
        if abs(x) >= 1e9:  return f"{x/1e9:,.2f} tỷ"
        if abs(x) >= 1e6:  return f"{x/1e6:,.1f} tr"
        if abs(x) >= 1e3:  return f"{x/1e3:,.0f}k"
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
        hoverlabel=dict(font_size=13),
    )
    if height:
        fig.update_layout(height=height)
    return fig


def empty_state(msg: str = "Không có dữ liệu phù hợp với bộ lọc hiện tại. Thử nới rộng khoảng thời gian hoặc chọn thêm Source/Channel ở cột lọc."):
    st.info(msg)
