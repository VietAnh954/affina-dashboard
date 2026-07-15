"""
Trang 5 — Chi tiết & Filter
- Filter chi tiết (text search, range slider)
- Interactive DataTable
- Download CSV / Excel
- Statistical summary
"""
import io

import pandas as pd
import streamlit as st

from lib.data import (
    DATE_COL,
    apply_filters, empty_state, fmt_num, fmt_vnd,
    load_master_data, render_sidebar_filters,
)

st.set_page_config(page_title="Chi tiết & Filter", page_icon=None, layout="wide")
st.title("Chi tiết & Filter")
st.caption("Tra cứu, filter theo nhiều điều kiện, xuất CSV/Excel cho phân tích riêng.")

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
# Advanced filter panel (bổ sung filter chi tiết)
# ============================================================================
st.markdown("### Filter chi tiết")

col_a, col_b, col_c = st.columns(3)

with col_a:
    q_contract = st.text_input("Số hợp đồng (chứa)")
    q_ndbh = st.text_input("Tên NĐBH (chứa)")

with col_b:
    q_nmbh = st.text_input("Tên NMBH (chứa)")
    q_sale = st.text_input("Tên sale (chứa)")

with col_c:
    if "Số tiền thanh toán" in df.columns:
        min_amount = int(df["Số tiền thanh toán"].dropna().min() or 0)
        max_amount = int(df["Số tiền thanh toán"].dropna().max() or 100_000_000)
        amount_range = st.slider(
            "Số tiền thanh toán (VNĐ)",
            min_value=min_amount, max_value=max_amount,
            value=(min_amount, max_amount),
            step=100_000,
            format="%d",
        )
    else:
        amount_range = None

# Additional filter: sale/BDM/BDD
col_d, col_e, col_f = st.columns(3)
with col_d:
    sale_list = sorted(df["Họ tên sale"].dropna().unique().tolist()) if "Họ tên sale" in df.columns else []
    sel_sale = st.multiselect("Sale cụ thể", sale_list, default=[])
with col_e:
    bdm_list = sorted(df["QUẢN LÝ CẤP 1 (BDM)"].dropna().unique().tolist()) if "QUẢN LÝ CẤP 1 (BDM)" in df.columns else []
    sel_bdm = st.multiselect("BDM cụ thể", bdm_list, default=[])
with col_f:
    bdd_list = sorted(df["QUẢN LÝ CẤP 2 (BDD)"].dropna().unique().tolist()) if "QUẢN LÝ CẤP 2 (BDD)" in df.columns else []
    sel_bdd = st.multiselect("BDD cụ thể", bdd_list, default=[])

# Apply advanced filters
df_view = df.copy()

if q_contract and "Số hợp đồng" in df_view.columns:
    df_view = df_view[df_view["Số hợp đồng"].astype(str).str.contains(q_contract, case=False, na=False)]
if q_ndbh and "Tên NĐBH" in df_view.columns:
    df_view = df_view[df_view["Tên NĐBH"].astype(str).str.contains(q_ndbh, case=False, na=False)]
if q_nmbh and "Tên NMBH" in df_view.columns:
    df_view = df_view[df_view["Tên NMBH"].astype(str).str.contains(q_nmbh, case=False, na=False)]
if q_sale and "Họ tên sale" in df_view.columns:
    df_view = df_view[df_view["Họ tên sale"].astype(str).str.contains(q_sale, case=False, na=False)]
if amount_range and "Số tiền thanh toán" in df_view.columns:
    df_view = df_view[(df_view["Số tiền thanh toán"] >= amount_range[0]) &
                      (df_view["Số tiền thanh toán"] <= amount_range[1])]
if sel_sale:
    df_view = df_view[df_view["Họ tên sale"].isin(sel_sale)]
if sel_bdm:
    df_view = df_view[df_view["QUẢN LÝ CẤP 1 (BDM)"].isin(sel_bdm)]
if sel_bdd:
    df_view = df_view[df_view["QUẢN LÝ CẤP 2 (BDD)"].isin(sel_bdd)]

st.divider()

# ============================================================================
# Statistical summary
# ============================================================================
st.markdown("### Tóm tắt kết quả filter")

if df_view.empty:
    empty_state("Không có bản ghi nào khớp với filter đang chọn.")
    st.stop()

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Số dòng", fmt_num(len(df_view)))
s2.metric("Số HĐ", fmt_num(df_view["Số hợp đồng"].nunique() if "Số hợp đồng" in df_view.columns else 0))
s3.metric("Tổng doanh thu", fmt_vnd(df_view["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df_view.columns else 0, short=True))
s4.metric("Tổng phí BH", fmt_vnd(df_view["Phí BH (VNĐ)"].sum() if "Phí BH (VNĐ)" in df_view.columns else 0, short=True))
avg_dt = (df_view["Doanh thu trước thuế"].sum() / df_view["Số hợp đồng"].nunique()
          if df_view["Số hợp đồng"].nunique() > 0 else 0)
s5.metric("AVG DT/HĐ", fmt_vnd(avg_dt, short=True))

if DATE_COL in df_view.columns:
    d_min = df_view[DATE_COL].min()
    d_max = df_view[DATE_COL].max()
    if pd.notna(d_min) and pd.notna(d_max):
        st.caption(f"Khoảng thời gian dữ liệu: **{d_min.strftime('%d/%m/%Y')}** → **{d_max.strftime('%d/%m/%Y')}**")

st.divider()

# ============================================================================
# Interactive DataTable
# ============================================================================
st.markdown("### Dữ liệu chi tiết")

# Chọn cột hiển thị
default_cols = [
    "Source", "Channel", "Ngày thanh toán", "Số hợp đồng",
    "Loại bảo hiểm", "Sản phẩm", "Nhà BH",
    "Tên NĐBH", "Tên NMBH",
    "Số tiền thanh toán", "Phí BH (VNĐ)", "Doanh thu trước thuế",
    "Họ tên sale", "Chức danh", "QUẢN LÝ CẤP 1 (BDM)", "QUẢN LÝ CẤP 2 (BDD)",
    "EST_Bonus", "Affina_Revenue", "Thưởng Teamlead",
    "Ngày bắt đầu", "Ngày kết thúc",
]
available_cols = [c for c in default_cols if c in df_view.columns]
extra_cols = [c for c in df_view.columns if c not in available_cols and c != "_ingested_at"]

show_cols = st.multiselect(
    "Chọn cột hiển thị",
    options=available_cols + extra_cols,
    default=available_cols,
)

if show_cols:
    df_show = df_view[show_cols].copy()

    # Column config
    col_cfg = {}
    for c in show_cols:
        if c in ["Số tiền thanh toán", "Phí BH (VNĐ)", "Doanh thu trước thuế",
                 "EST_Bonus", "Affina_Revenue", "Thưởng Teamlead"]:
            col_cfg[c] = st.column_config.NumberColumn(c, format="%.0f ₫")
        elif c in [DATE_COL, "Ngày bắt đầu", "Ngày kết thúc"]:
            col_cfg[c] = st.column_config.DateColumn(c, format="DD/MM/YYYY")

    st.dataframe(
        df_show,
        column_config=col_cfg,
        use_container_width=True,
        hide_index=True,
        height=500,
    )
else:
    st.info("Chưa chọn cột nào để hiển thị.")

st.divider()

# ============================================================================
# Download
# ============================================================================
st.markdown("### Tải xuống")

d_left, d_right = st.columns(2)

with d_left:
    csv_data = df_view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Tải CSV",
        data=csv_data,
        file_name=f"affina_dashboard_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with d_right:
    # Excel export
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Không ghi cột _ingested_at cho gọn
        cols_out = [c for c in df_view.columns if c != "_ingested_at"]
        df_view[cols_out].to_excel(writer, sheet_name="Data", index=False)
    buf.seek(0)
    st.download_button(
        "Tải Excel",
        data=buf.getvalue(),
        file_name=f"affina_dashboard_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
