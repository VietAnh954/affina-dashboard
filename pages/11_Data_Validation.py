"""
TRANG 11 — DATA VALIDATION
So sánh dữ liệu dashboard (từ Supabase) với database tổng (upload Excel).
Mục đích: phát hiện sai lệch số liệu giữa 2 nguồn.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.data import (
    DATE_COL, apply_plotly_layout, empty_state, fmt_num, fmt_vnd,
    load_master_data,
)

st.set_page_config(page_title="Data Validation", layout="wide")

from lib.auth import require_auth
require_auth("home", "Data Validation")


# ============================================================================
# HELPERS
# ============================================================================
def _norm_str(s):
    if pd.isna(s):
        return ""
    return str(s).strip().upper()


def _safe_date(s):
    return pd.to_datetime(s, errors="coerce")


def _compare_metric(label, val_dash, val_db, fmt_fn=None):
    """Hiển thị 1 metric so sánh: dashboard vs DB."""
    if fmt_fn is None:
        fmt_fn = lambda x: f"{x:,.0f}"
    diff = val_dash - val_db
    pct = (diff / val_db * 100) if val_db != 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{label} (Dashboard)", fmt_fn(val_dash))
    c2.metric(f"{label} (DB Tong)", fmt_fn(val_db))
    color = "red" if abs(pct) > 1 else "green"
    c3.metric("Chenh lech", fmt_fn(diff), delta=f"{pct:+.2f}%")
    return {"label": label, "dashboard": val_dash, "db_tong": val_db, "diff": diff, "pct": pct}


# ============================================================================
# MAIN
# ============================================================================
st.title("Data Validation — So sanh Dashboard vs Database Tong")
st.caption(
    "Upload file database_tong.xlsx de so sanh voi du lieu dang hien thi tren dashboard. "
    "Phat hien chenh lech so lieu."
)

# Load dashboard data
df_dash = load_master_data()
if df_dash.empty:
    st.warning("Chua co du lieu dashboard.")
    st.stop()

df_dash[DATE_COL] = pd.to_datetime(df_dash[DATE_COL], errors="coerce")

# Upload DB tong
st.markdown("### 1. Upload file Database Tong")
uploaded = st.file_uploader("Chon file database_tong.xlsx", type=["xlsx", "xls"])

if uploaded is None:
    st.info("Upload file database_tong.xlsx de bat dau so sanh.")
    st.stop()

# Read DB tong
with st.spinner("Dang doc file..."):
    df_db = pd.read_excel(uploaded, sheet_name=0)

df_db["Ngày thanh toán"] = _safe_date(df_db["Ngày thanh toán"])
df_db["Số tiền thanh toán"] = pd.to_numeric(df_db["Số tiền thanh toán"], errors="coerce")

st.success(f"Da doc: **{len(df_db):,}** dong, **{len(df_db.columns)}** cot")

# Filter cùng khoảng thời gian
st.markdown("### 2. Chon khoang thoi gian so sanh")
col1, col2 = st.columns(2)
with col1:
    years = sorted(df_db["Ngày thanh toán"].dropna().dt.year.unique().astype(int))
    sel_years = st.multiselect("Nam", options=years, default=[y for y in years if y >= 2024])
with col2:
    st.caption(f"Dashboard: {df_dash[DATE_COL].min().strftime('%d/%m/%Y')} - {df_dash[DATE_COL].max().strftime('%d/%m/%Y')}")
    st.caption(f"DB Tong: {df_db['Ngày thanh toán'].min().strftime('%d/%m/%Y')} - {df_db['Ngày thanh toán'].max().strftime('%d/%m/%Y')}")

if sel_years:
    df_db_f = df_db[df_db["Ngày thanh toán"].dt.year.isin(sel_years)]
    df_dash_f = df_dash[df_dash[DATE_COL].dt.year.isin(sel_years)]
else:
    df_db_f = df_db
    df_dash_f = df_dash

st.divider()

# ============================================================================
# 3. TONG QUAN SO SANH
# ============================================================================
st.markdown("### 3. Tong quan — So sanh chi so chinh")

results = []

# Row count
results.append(_compare_metric(
    "Tong so dong", len(df_dash_f), len(df_db_f),
    fmt_fn=lambda x: f"{int(x):,}"
))

# Total payment
dash_payment = df_dash_f["Số tiền thanh toán"].sum() if "Số tiền thanh toán" in df_dash_f else 0
db_payment = df_db_f["Số tiền thanh toán"].sum()
results.append(_compare_metric(
    "Tong so tien thanh toan",
    dash_payment, db_payment,
    fmt_fn=lambda x: fmt_vnd(x, short=True)
))

# Revenue
dash_rev = df_dash_f["Doanh thu trước thuế"].sum() if "Doanh thu trước thuế" in df_dash_f else 0
results.append(_compare_metric(
    "Doanh thu truoc thue (Dashboard only)",
    dash_rev, 0,
    fmt_fn=lambda x: fmt_vnd(x, short=True)
))

# Contract count
dash_hd = df_dash_f["Số hợp đồng"].nunique() if "Số hợp đồng" in df_dash_f else 0
db_hd = df_db_f["Số hợp đồng"].nunique() if "Số hợp đồng" in df_db_f else 0
results.append(_compare_metric(
    "So hop dong (unique)",
    dash_hd, db_hd,
    fmt_fn=lambda x: f"{int(x):,}"
))

st.divider()

# ============================================================================
# 4. SO SANH THEO LOAI BAO HIEM
# ============================================================================
st.markdown("### 4. So sanh theo Loai bao hiem")

if "Loại bảo hiểm" in df_dash_f.columns and "Loại bảo hiểm" in df_db_f.columns:
    dash_by_type = df_dash_f.groupby("Loại bảo hiểm").agg(
        dash_count=("Số hợp đồng", "nunique") if "Số hợp đồng" in df_dash_f else ("Loại bảo hiểm", "count"),
        dash_payment=("Số tiền thanh toán", "sum"),
    )
    db_by_type = df_db_f.groupby("Loại bảo hiểm").agg(
        db_count=("Số hợp đồng", "nunique") if "Số hợp đồng" in df_db_f else ("Loại bảo hiểm", "count"),
        db_payment=("Số tiền thanh toán", "sum"),
    )
    comp_type = dash_by_type.join(db_by_type, how="outer").fillna(0)
    comp_type["diff_count"] = comp_type["dash_count"] - comp_type["db_count"]
    comp_type["diff_payment"] = comp_type["dash_payment"] - comp_type["db_payment"]
    comp_type["diff_pct"] = np.where(
        comp_type["db_payment"] != 0,
        (comp_type["diff_payment"] / comp_type["db_payment"] * 100).round(2),
        0
    )
    comp_type = comp_type.sort_values("db_payment", ascending=False)

    # Highlight dòng sai lệch > 5%
    st.dataframe(
        comp_type.style.apply(
            lambda row: ["background-color: #FFE0E0" if abs(row["diff_pct"]) > 5 else "" for _ in row],
            axis=1,
        ),
        use_container_width=True,
        column_config={
            "dash_count": st.column_config.NumberColumn("HD Dashboard", format="%d"),
            "db_count": st.column_config.NumberColumn("HD DB Tong", format="%d"),
            "dash_payment": st.column_config.NumberColumn("Thanh toan Dashboard", format="%.0f"),
            "db_payment": st.column_config.NumberColumn("Thanh toan DB", format="%.0f"),
            "diff_count": st.column_config.NumberColumn("Chenh HD", format="%d"),
            "diff_payment": st.column_config.NumberColumn("Chenh tien", format="%.0f"),
            "diff_pct": st.column_config.NumberColumn("Chenh %", format="%.2f%%"),
        },
    )

    # Bar chart so sánh
    comp_melt = comp_type[["dash_payment", "db_payment"]].reset_index()
    comp_melt = comp_melt.melt(id_vars="Loại bảo hiểm", var_name="Nguon", value_name="Tien")
    comp_melt["Nguon"] = comp_melt["Nguon"].map({"dash_payment": "Dashboard", "db_payment": "DB Tong"})
    fig = px.bar(
        comp_melt, x="Loại bảo hiểm", y="Tien", color="Nguon",
        barmode="group", text_auto=".2s",
        color_discrete_map={"Dashboard": "#B44BC8", "DB Tong": "#8B6FC9"},
    )
    fig.update_yaxes(tickformat=",")
    st.plotly_chart(apply_plotly_layout(fig, title="So tien thanh toan: Dashboard vs DB Tong", height=400),
                    use_container_width=True)

st.divider()

# ============================================================================
# 5. SO SANH THEO CHANNEL
# ============================================================================
st.markdown("### 5. So sanh theo Channel")

if "Channel" in df_db_f.columns:
    # Chuẩn hóa channel names
    dash_ch = df_dash_f.groupby("Channel")["Số tiền thanh toán"].agg(["count", "sum"]).rename(
        columns={"count": "dash_rows", "sum": "dash_payment"}
    ) if "Channel" in df_dash_f.columns else pd.DataFrame()

    db_ch = df_db_f.groupby("Channel")["Số tiền thanh toán"].agg(["count", "sum"]).rename(
        columns={"count": "db_rows", "sum": "db_payment"}
    )

    if not dash_ch.empty:
        comp_ch = dash_ch.join(db_ch, how="outer").fillna(0)
        comp_ch["diff_payment"] = comp_ch["dash_payment"] - comp_ch["db_payment"]
        comp_ch["diff_pct"] = np.where(
            comp_ch["db_payment"] != 0,
            (comp_ch["diff_payment"] / comp_ch["db_payment"] * 100).round(2), 0
        )
        comp_ch = comp_ch.sort_values("db_payment", ascending=False)
        st.dataframe(comp_ch, use_container_width=True)

        # Warning for channels only in one source
        only_dash = set(df_dash_f["Channel"].dropna().unique()) - set(df_db_f["Channel"].dropna().unique())
        only_db = set(df_db_f["Channel"].dropna().unique()) - set(df_dash_f["Channel"].dropna().unique()) if "Channel" in df_dash_f.columns else set()
        if only_dash:
            st.warning(f"Channel CHI CO trong Dashboard: {', '.join(sorted(only_dash))}")
        if only_db:
            st.warning(f"Channel CHI CO trong DB Tong: {', '.join(sorted(only_db))}")

st.divider()

# ============================================================================
# 6. SO SANH THEO THANG
# ============================================================================
st.markdown("### 6. So sanh theo Thang")

if DATE_COL in df_dash_f.columns and "Ngày thanh toán" in df_db_f.columns:
    dash_monthly = (df_dash_f.groupby(df_dash_f[DATE_COL].dt.to_period("M"))["Số tiền thanh toán"]
                        .sum().reset_index())
    dash_monthly.columns = ["month", "dashboard"]
    dash_monthly["month"] = dash_monthly["month"].astype(str)

    db_monthly = (df_db_f.groupby(df_db_f["Ngày thanh toán"].dt.to_period("M"))["Số tiền thanh toán"]
                      .sum().reset_index())
    db_monthly.columns = ["month", "db_tong"]
    db_monthly["month"] = db_monthly["month"].astype(str)

    comp_m = pd.merge(dash_monthly, db_monthly, on="month", how="outer").fillna(0).sort_values("month")
    comp_m["diff"] = comp_m["dashboard"] - comp_m["db_tong"]
    comp_m["diff_pct"] = np.where(comp_m["db_tong"] != 0, (comp_m["diff"] / comp_m["db_tong"] * 100).round(2), 0)

    # Line chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=comp_m["month"], y=comp_m["dashboard"],
                              mode="lines+markers", name="Dashboard", line=dict(color="#B44BC8", width=2.5)))
    fig.add_trace(go.Scatter(x=comp_m["month"], y=comp_m["db_tong"],
                              mode="lines+markers", name="DB Tong", line=dict(color="#8B6FC9", width=2.5, dash="dash")))
    fig.update_yaxes(tickformat=",")
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(apply_plotly_layout(fig, title="Thanh toan theo thang: Dashboard vs DB Tong", height=400),
                    use_container_width=True)

    # Table with highlighting
    st.dataframe(
        comp_m.style.apply(
            lambda row: ["background-color: #FFE0E0" if abs(row["diff_pct"]) > 10 else "" for _ in row],
            axis=1,
        ),
        column_config={
            "dashboard": st.column_config.NumberColumn("Dashboard", format="%.0f"),
            "db_tong": st.column_config.NumberColumn("DB Tong", format="%.0f"),
            "diff": st.column_config.NumberColumn("Chenh lech", format="%.0f"),
            "diff_pct": st.column_config.NumberColumn("Chenh %", format="%.2f%%"),
        },
        use_container_width=True, hide_index=True,
    )

st.divider()

# ============================================================================
# 7. KHOP HOP DONG — Tim HD thieu/thua
# ============================================================================
st.markdown("### 7. Khop hop dong — Tim HD thieu / thua")

if "Số hợp đồng" in df_dash_f.columns and "Số hợp đồng" in df_db_f.columns:
    dash_hd_set = set(df_dash_f["Số hợp đồng"].dropna().apply(_norm_str))
    db_hd_set = set(df_db_f["Số hợp đồng"].dropna().apply(_norm_str))

    only_in_dash = dash_hd_set - db_hd_set
    only_in_db = db_hd_set - dash_hd_set
    in_both = dash_hd_set & db_hd_set

    c1, c2, c3 = st.columns(3)
    c1.metric("HD co trong CA 2 nguon", fmt_num(len(in_both)))
    c2.metric("CHI CO trong Dashboard", fmt_num(len(only_in_dash)),
              delta=f"{len(only_in_dash)} HD", delta_color="inverse")
    c3.metric("CHI CO trong DB Tong", fmt_num(len(only_in_db)),
              delta=f"{len(only_in_db)} HD", delta_color="inverse")

    # Venn-like bar
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Co trong ca 2", "Chi Dashboard", "Chi DB Tong"],
                          y=[len(in_both), len(only_in_dash), len(only_in_db)],
                          marker_color=["#5FBFA0", "#E85BD8", "#8B6FC9"],
                          text=[len(in_both), len(only_in_dash), len(only_in_db)],
                          textposition="outside"))
    st.plotly_chart(apply_plotly_layout(fig, title="Phan bo hop dong", height=350),
                    use_container_width=True)

    # Show HD chỉ có trong 1 nguồn
    tab_dash_only, tab_db_only = st.tabs(["HD chi co trong Dashboard", "HD chi co trong DB Tong"])

    with tab_dash_only:
        if only_in_dash:
            df_only_dash = df_dash_f[df_dash_f["Số hợp đồng"].apply(_norm_str).isin(only_in_dash)]
            show_cols = [c for c in [DATE_COL, "Số hợp đồng", "Loại bảo hiểm", "Sản phẩm",
                                      "Channel", "Số tiền thanh toán", "Họ tên sale"] if c in df_only_dash.columns]
            st.dataframe(df_only_dash[show_cols].head(500), hide_index=True, use_container_width=True)
            st.caption(f"Hien thi {min(500, len(df_only_dash))}/{len(df_only_dash)} dong")
        else:
            st.success("Khong co HD nao chi co trong Dashboard.")

    with tab_db_only:
        if only_in_db:
            df_only_db = df_db_f[df_db_f["Số hợp đồng"].apply(_norm_str).isin(only_in_db)]
            show_cols = [c for c in ["Ngày thanh toán", "Số hợp đồng", "Loại bảo hiểm", "Sản phẩm",
                                      "Channel", "Số tiền thanh toán", "Tên sale"] if c in df_only_db.columns]
            st.dataframe(df_only_db[show_cols].head(500), hide_index=True, use_container_width=True)
            st.caption(f"Hien thi {min(500, len(df_only_db))}/{len(df_only_db)} dong")
        else:
            st.success("Khong co HD nao chi co trong DB Tong.")

st.divider()

# ============================================================================
# 8. SO SANH CHI TIET HD TRUNG — Tim sai lech gia tri
# ============================================================================
st.markdown("### 8. HD trung nhung so tien KHAC nhau")

if "Số hợp đồng" in df_dash_f.columns and "Số hợp đồng" in df_db_f.columns:
    # Aggregate per contract
    dash_agg = (df_dash_f.groupby(df_dash_f["Số hợp đồng"].apply(_norm_str))["Số tiền thanh toán"]
                    .sum().reset_index())
    dash_agg.columns = ["hd_norm", "dash_payment"]

    db_agg = (df_db_f.groupby(df_db_f["Số hợp đồng"].apply(_norm_str))["Số tiền thanh toán"]
                  .sum().reset_index())
    db_agg.columns = ["hd_norm", "db_payment"]

    merged = pd.merge(dash_agg, db_agg, on="hd_norm", how="inner")
    merged["diff"] = merged["dash_payment"] - merged["db_payment"]
    merged["abs_diff"] = merged["diff"].abs()
    merged["diff_pct"] = np.where(merged["db_payment"] != 0,
                                    (merged["diff"] / merged["db_payment"] * 100).round(2), 0)

    # Filter chỉ HD có chênh lệch
    threshold = st.slider("Nguong chenh lech toi thieu (VND)", 0, 1_000_000, 100, step=100,
                           key="diff_threshold")
    mismatched = merged[merged["abs_diff"] > threshold].sort_values("abs_diff", ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("HD trung (match)", fmt_num(len(merged)))
    c2.metric("HD co chenh lech", fmt_num(len(mismatched)),
              delta=f"{len(mismatched)/max(len(merged),1)*100:.1f}%", delta_color="inverse")
    c3.metric("Tong chenh lech tuyet doi",
              fmt_vnd(mismatched["abs_diff"].sum(), short=True))

    if not mismatched.empty:
        st.dataframe(
            mismatched.head(200),
            column_config={
                "hd_norm": "So hop dong",
                "dash_payment": st.column_config.NumberColumn("Dashboard", format="%.0f"),
                "db_payment": st.column_config.NumberColumn("DB Tong", format="%.0f"),
                "diff": st.column_config.NumberColumn("Chenh lech", format="%.0f"),
                "diff_pct": st.column_config.NumberColumn("Chenh %", format="%.2f%%"),
            },
            hide_index=True, use_container_width=True,
        )
        st.caption(f"Hien thi {min(200, len(mismatched))}/{len(mismatched)} HD co chenh lech")

        # Distribution of differences
        fig = px.histogram(mismatched, x="diff", nbins=50, color_discrete_sequence=["#E85BD8"])
        fig.update_xaxes(title="Chenh lech (VND)", tickformat=",")
        fig.update_yaxes(title="So HD")
        st.plotly_chart(apply_plotly_layout(fig, title="Phan bo chenh lech", height=350),
                        use_container_width=True)
    else:
        st.success(f"Tat ca {len(merged):,} HD trung deu khop so tien (nguong {threshold:,} VND).")

st.divider()

# ============================================================================
# 9. NGUON CAP DON ANALYSIS
# ============================================================================
st.markdown("### 9. Phan tich Nguon cap don (DB Tong)")

if "Nguồn cấp đơn" in df_db_f.columns:
    nguon = df_db_f.groupby("Nguồn cấp đơn").agg(
        n_rows=("Số hợp đồng", "count"),
        n_hd=("Số hợp đồng", "nunique"),
        total=("Số tiền thanh toán", "sum"),
    ).sort_values("total", ascending=False)
    st.dataframe(nguon, use_container_width=True)
    st.caption(
        "**Chi Capdon**: chi co trong Google Sheet cap don (nguon dashboard). "
        "**Chi DB**: chi co trong database he thong. "
        "**Ca 2**: co trong ca 2 nguon."
    )

st.divider()

# ============================================================================
# 10. SUMMARY & RECOMMENDATIONS
# ============================================================================
st.markdown("### 10. Tom tat & Khuyen nghi")

summary_items = []
for r in results:
    if abs(r["pct"]) > 5:
        summary_items.append(f"- **{r['label']}**: chenh {r['pct']:+.2f}% (Dashboard: {r['dashboard']:,.0f} vs DB: {r['db_tong']:,.0f})")

if summary_items:
    st.warning("**Cac chi so co chenh lech > 5%:**\n" + "\n".join(summary_items))
else:
    st.success("Tat ca chi so chinh chenh lech < 5%. Du lieu kha dong nhat.")

st.markdown("""
**Nguyen nhan chenh lech thuong gap:**
- Dashboard chi lay data tu Google Sheet cap don, DB Tong lay tu he thong backend
- Dashboard chi filter nam 2024-2026, DB Tong co tu 2022
- Channel naming khac nhau giua 2 nguon (VD: 'DSA' trong DB = 'Core Agency' trong capdon)
- HD bi trung hoac bi xoa o 1 nguon nhung chua cap nhat nguon kia
- Ngay thanh toan co the bi dich do clean data khac nhau

**Khuyen nghi:**
1. Kiem tra cac HD **chi co trong 1 nguon** — co the la HD bi thieu
2. Kiem tra cac HD **trung nhung chenh tien** — co the la loi nhap lieu
3. Map lai Channel names giua 2 nguon de so sanh chinh xac hon
""")
