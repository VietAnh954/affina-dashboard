"""
lib/data.py — Shared utilities cho toàn bộ Streamlit dashboard

- Load data từ Parquet (GitHub Release) hoặc Supabase (fallback)
- Load dashboard_meta (last update info)
- Helper format số VNĐ, ngày
- Global filter application
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
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
DEFAULT_TTL = 1800  # 30 phút — giảm tải Supabase (Phase 0)

SERVING_COLUMNS = [
    "Ngày thanh toán", "Ngày bắt đầu", "Ngày kết thúc", "Ngày sinh NĐBH", "Ngày sinh NMBH",
    "Số hợp đồng", "Sản phẩm", "Nhà BH", "Loại bảo hiểm",
    "Đối tác nhà bảo hiểm", "Ngoại trú", "Nha khoa", "Thai sản", "Topup",
    "Source", "Channel", "Channel Sales",
    "Họ tên sale", "Họ tên", "Chức danh", "SĐT sale",
    "QUẢN LÝ CẤP 1 (BDM)", "QUẢN LÝ CẤP 2 (BDD)", "Quản lý Cấp 3 (BDH)",
    "Số tiền thanh toán", "Phí BH (VNĐ)", "Doanh thu trước thuế",
    "EST_Bonus", "Affina_Revenue", "Incentive OVE", "Thưởng Teamlead",
    "SM_OR", "SD_OR", "SM_IO", "SD_IO", "BDM_bonus", "BDD_bonus",
    "Chi Agency", "Chi QL", "Budget Neo T6",
    "rate_bonus", "Affina_rate_bonus", "exchange_core",
    "Tên NĐBH", "Giới tính NNBH", "CCCD NĐBH",
    "Tên NMBH", "CCCD NMBH", "Quan hệ", "SĐT NMBH", "Email NMBH", "Địa chỉ NMBH",
    "_ingested_at",
]


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
GITHUB_REPO = "VietAnh954/affina-dashboard"
PARQUET_TAG = "data-latest"
PARQUET_ASSET = "serving.parquet"


def _get_github_token() -> str | None:
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return os.environ.get("GITHUB_TOKEN")


def _load_from_parquet() -> pd.DataFrame | None:
    token = _get_github_token()
    if not token:
        return None
    try:
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{PARQUET_TAG}"
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        assets = resp.json().get("assets", [])
        asset_url = None
        for a in assets:
            if a["name"] == PARQUET_ASSET:
                asset_url = a["url"]
                break
        if not asset_url:
            return None
        dl_headers = {"Authorization": f"token {token}", "Accept": "application/octet-stream"}
        dl_resp = requests.get(asset_url, headers=dl_headers, timeout=60)
        if dl_resp.status_code != 200:
            return None
        return pd.read_parquet(io.BytesIO(dl_resp.content))
    except Exception:
        return None


def _load_from_supabase() -> pd.DataFrame:
    engine = get_engine()
    cols_sql = ", ".join(f'"{c}"' for c in SERVING_COLUMNS)
    return pd.read_sql(text(f"SELECT {cols_sql} FROM dashboard.master_data"), engine)


@st.cache_data(ttl=DEFAULT_TTL, show_spinner="Đang tải data...")
def load_master_data() -> pd.DataFrame:
    df = _load_from_parquet()
    if df is None:
        try:
            df = _load_from_supabase()
        except Exception as e:
            st.error(f"Không đọc được data: {e}")
            st.info("Vào GitHub Actions → Build Dashboard Data → Run workflow.")
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
            "SELECT * FROM dashboard.meta ORDER BY id DESC LIMIT 1"
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
    """
    from lib.i18n import t, render_logo, render_lang_switch

    # Logo trên cùng sidebar
    render_logo()

    # Language switch
    render_lang_switch()

    st.sidebar.divider()
    st.sidebar.markdown(f"### {t('filter_title')}")

    # Date range
    date_min = df[DATE_COL].min()
    date_max = df[DATE_COL].max()
    if pd.isna(date_min):
        date_min = pd.Timestamp("2024-01-01")
    if pd.isna(date_max):
        date_max = pd.Timestamp.today()

    date_range = st.sidebar.date_input(
        t("filter_date"),
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
        t("filter_source"), options=sources, default=sources
    )

    # Channel
    channels = sorted(df["Channel"].dropna().unique().tolist()) if "Channel" in df.columns else []
    selected_channels = st.sidebar.multiselect(
        t("filter_channel"), options=channels, default=channels
    )

    # Loai BH
    loai_bh = sorted(df["Loại bảo hiểm"].dropna().unique().tolist()) if "Loại bảo hiểm" in df.columns else []
    selected_loai = st.sidebar.multiselect(
        t("filter_loaibh"), options=loai_bh, default=loai_bh
    )

    # Nha BH
    nha_bh = sorted(df["Nhà BH"].dropna().unique().tolist()) if "Nhà BH" in df.columns else []
    selected_nha = st.sidebar.multiselect(
        t("filter_nhabh"), options=nha_bh, default=[],
        help=t("filter_empty_all"),
    )

    st.sidebar.divider()

    # Refresh button
    if st.sidebar.button(t("btn_refresh"), use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()

    # Meta info
    meta = load_meta()
    if meta:
        updated_at = meta.get("updated_at")
        if updated_at is not None:
            if isinstance(updated_at, str):
                updated_at = pd.to_datetime(updated_at)
            if updated_at.tzinfo is None:
                updated_at = updated_at.tz_localize("UTC")
            vn_time = updated_at.astimezone(timezone(timedelta(hours=7)))
            st.sidebar.caption(f"{t('last_updated')}:\n**{vn_time.strftime('%d/%m/%Y %H:%M')}** (VN)")
        st.sidebar.caption(f"{t('total_rows')}: **{meta.get('row_count', 0):,}**")

    st.sidebar.divider()
    st.sidebar.caption("Affina Sales Dashboard")

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

# ============================================================================
# Formatting helpers (i18n from lib/i18n.py)
# ============================================================================
def fmt_vnd(x, short: bool = False) -> str:
    if pd.isna(x):
        return "-"
    x = float(x)
    from lib.i18n import get_lang
    lang = get_lang()
    if short:
        if lang == "vi":
            units = [("nghin ty", 1e12), ("ty", 1e9), ("tr", 1e6), ("k", 1e3)]
        else:
            units = [("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)]
        for unit, div in units:
            if abs(x) >= div:
                val = x / div
                if abs(val) < 10:
                    return f"{val:,.2f} {unit}"
                elif abs(val) < 100:
                    return f"{val:,.1f} {unit}"
                else:
                    return f"{val:,.0f} {unit}"
        return f"{x:,.0f}"
    return f"{x:,.0f}"


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
