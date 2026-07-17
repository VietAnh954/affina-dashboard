"""
lib/i18n.py — Internationalization module
Full translation VI <-> EN for Affina Dashboard.
"""
from __future__ import annotations
import streamlit as st

_LOCALE = {
    # Navigation
    "nav_dashboard":       {"vi": "Trang chu",            "en": "Dashboard"},
    "nav_kenh":            {"vi": "Kenh & San pham",       "en": "Channels & Products"},
    "nav_sales":           {"vi": "Doi ngu Sales",         "en": "Sales Team"},
    "nav_time":            {"vi": "Phan tich thoi gian",   "en": "Time Analysis"},
    "nav_export":          {"vi": "Chi tiet & Export",     "en": "Details & Export"},
    "nav_headsale":        {"vi": "Head Sale Dashboard",   "en": "Head Sale Dashboard"},
    "nav_executive":       {"vi": "Executive Insights",    "en": "Executive Insights"},
    "nav_customer":        {"vi": "Customer Analytics",    "en": "Customer Analytics"},
    "nav_forecast":        {"vi": "Forecast & Anomaly",    "en": "Forecast & Anomaly"},
    "nav_kpi":             {"vi": "KPI Competition",       "en": "KPI Competition"},
    # Sidebar
    "filter_title":        {"vi": "Bo loc chung",          "en": "Global Filters"},
    "filter_date":         {"vi": "Khoang thoi gian",      "en": "Date Range"},
    "filter_source":       {"vi": "Source",                 "en": "Source"},
    "filter_channel":      {"vi": "Channel",                "en": "Channel"},
    "filter_loaibh":       {"vi": "Loai bao hiem",         "en": "Insurance Type"},
    "filter_nhabh":        {"vi": "Nha bao hiem",          "en": "Insurer"},
    "filter_empty_all":    {"vi": "De trong = tat ca",     "en": "Leave empty = all"},
    "btn_refresh":         {"vi": "Lam moi du lieu",       "en": "Refresh Data"},
    "last_updated":        {"vi": "Data cap nhat",         "en": "Last updated"},
    "total_rows":          {"vi": "Tong so dong",          "en": "Total rows"},
    # Home
    "home_title":          {"vi": "Affina Sales Dashboard", "en": "Affina Sales Dashboard"},
    "home_subtitle":       {"vi": "Tram viec da kho, Bao hiem co Affina lo", "en": "Insurance Made Easy with Affina"},
    "home_kpi_title":      {"vi": "Chi so kinh doanh chinh", "en": "Key Business Metrics"},
    "home_trend_title":    {"vi": "Xu huong & Co cau",       "en": "Trends & Structure"},
    "home_30d_title":      {"vi": "30 ngay gan nhat",        "en": "Last 30 Days"},
    "home_top10_title":    {"vi": "Top 10",                  "en": "Top 10"},
    "home_explore":        {"vi": "Kham pha sau hon",        "en": "Explore More"},
    # KPI labels
    "kpi_revenue":         {"vi": "Doanh thu truoc thue",    "en": "Pre-tax Revenue"},
    "kpi_payment":         {"vi": "Tong thanh toan",         "en": "Total Payment"},
    "kpi_contracts":       {"vi": "So hop dong",             "en": "Contracts"},
    "kpi_affina_rev":      {"vi": "Affina Revenue",          "en": "Affina Revenue"},
    "kpi_est_bonus":       {"vi": "EST Bonus",               "en": "EST Bonus"},
    "kpi_premium":         {"vi": "Phi BH (Premium)",        "en": "Insurance Premium"},
    "kpi_active_sales":    {"vi": "Sale hoat dong",          "en": "Active Sales"},
    "kpi_avg_per_hd":      {"vi": "TB Doanh thu / HD",       "en": "Avg Revenue / Contract"},
    "kpi_vs_prev":         {"vi": "so ky truoc",             "en": "vs prev period"},
    # Charts
    "chart_rev_by_month":  {"vi": "Doanh thu theo thang (chia theo Source)", "en": "Monthly Revenue (by Source)"},
    "chart_rev_structure": {"vi": "Co cau doanh thu theo Source",            "en": "Revenue Structure by Source"},
    "chart_rev_per_day":   {"vi": "Doanh thu / ngay",       "en": "Revenue / day"},
    "chart_hd_per_day":    {"vi": "So HD / ngay",            "en": "Contracts / day"},
    "chart_affina_per_day":{"vi": "Affina Revenue / ngay",   "en": "Affina Revenue / day"},
    "chart_total_30d":     {"vi": "Tong 30 ngay",            "en": "30-day Total"},
    "chart_avg_day":       {"vi": "TB / ngay",               "en": "Avg / day"},
    # Tables
    "tbl_top_sale":        {"vi": "Top 10 Sale theo Doanh thu",              "en": "Top 10 Sales by Revenue"},
    "tbl_top_partner":     {"vi": "Top 10 Nha bao hiem theo Doanh thu",     "en": "Top 10 Insurers by Revenue"},
    "tbl_rank":            {"vi": "Hang",              "en": "Rank"},
    "tbl_name":            {"vi": "Ho ten",             "en": "Name"},
    "tbl_revenue":         {"vi": "Doanh thu",          "en": "Revenue"},
    "tbl_contracts":       {"vi": "So HD",              "en": "Contracts"},
    # Buttons
    "btn_download_csv":    {"vi": "Tai CSV (nhanh)",         "en": "Download CSV (fast)"},
    "btn_download_excel":  {"vi": "Tai Excel (format dep)",  "en": "Download Excel (formatted)"},
    # Page titles
    "page_kenh_title":     {"vi": "Kenh & San pham",         "en": "Channels & Products"},
    "page_kenh_sub":       {"vi": "Phan tich theo kenh, loai BH, san pham.", "en": "Analysis by channel, insurance type, product."},
    "page_sales_title":    {"vi": "Doi ngu Sales",           "en": "Sales Team"},
    "page_sales_sub":      {"vi": "Ranking sale, hieu suat BDM/BDD.", "en": "Sales ranking, BDM/BDD performance."},
    "page_time_title":     {"vi": "Phan tich thoi gian",     "en": "Time Analysis"},
    "page_time_sub":       {"vi": "YoY, MoM, heatmap, xu huong.", "en": "YoY, MoM, heatmap, trends."},
    "page_export_title":   {"vi": "Chi tiet & Export",       "en": "Details & Export"},
    "page_export_sub":     {"vi": "Filter, preview, tai Excel/CSV.", "en": "Filter, preview, download Excel/CSV."},
    "page_head_title":     {"vi": "Head Sale Dashboard",     "en": "Head Sale Dashboard"},
    "page_exec_title":     {"vi": "Executive Insights",      "en": "Executive Insights"},
    "page_cust_title":     {"vi": "Customer Analytics",      "en": "Customer Analytics"},
    "page_forecast_title": {"vi": "Forecast & Anomaly",      "en": "Forecast & Anomaly"},
    "page_kpi_title":      {"vi": "KPI Competition — CLB Tinh Hoa Affina", "en": "KPI Competition — Affina Elite Club"},
    # Sections
    "sec_sunburst":        {"vi": "Sunburst: Source > Channel > Loai BH > San pham", "en": "Sunburst: Source > Channel > Type > Product"},
    "sec_channel_rev":     {"vi": "Doanh thu theo Channel",    "en": "Revenue by Channel"},
    "sec_partner_rev":     {"vi": "Nha bao hiem — Doanh thu theo Loai BH", "en": "Insurer — Revenue by Type"},
    "sec_top_products":    {"vi": "Top 15 san pham",           "en": "Top 15 Products"},
    "sec_loaibh_pie":      {"vi": "Co cau Loai bao hiem",     "en": "Insurance Type Structure"},
    "sec_bhsk_addons":     {"vi": "BHSK Add-ons",              "en": "Health Insurance Add-ons"},
    "sec_top20_sale":      {"vi": "Top 20 Salesperson",        "en": "Top 20 Salespersons"},
    "sec_bdm_perf":        {"vi": "Hieu suat BDM (Cap 1)",    "en": "BDM Performance (Level 1)"},
    "sec_bdd_perf":        {"vi": "Hieu suat BDD (Cap 2)",    "en": "BDD Performance (Level 2)"},
    "sec_hierarchy":       {"vi": "Cau truc nhanh: BDD — BDM", "en": "Branch: BDD — BDM"},
    "sec_scatter":         {"vi": "Scatter: So HD x Doanh thu", "en": "Scatter: Contracts x Revenue"},
    "sec_detail_table":    {"vi": "Bang chi tiet Sales",        "en": "Sales Detail Table"},
    "sec_yoy":             {"vi": "So sanh cung ky (YoY)",      "en": "Year-over-Year"},
    "sec_mom":             {"vi": "Tang truong thang (MoM)",    "en": "Month-over-Month Growth"},
    "sec_heatmap":         {"vi": "Heatmap: Thu x Tuan",        "en": "Heatmap: Day x Week"},
    "sec_cumulative":      {"vi": "Doanh thu cong don",         "en": "Cumulative Revenue"},
    "sec_expiry":          {"vi": "HD sap het han",              "en": "Expiring Contracts"},
    # Export
    "exp_template":        {"vi": "Chon template",              "en": "Choose Template"},
    "exp_structure":       {"vi": "Cau truc file",              "en": "File Structure"},
    "exp_preview":         {"vi": "Preview (20 dong dau)",      "en": "Preview (first 20 rows)"},
    "exp_download":        {"vi": "Tai xuong",                  "en": "Download"},
    "exp_advanced":        {"vi": "Bo loc nang cao",            "en": "Advanced Filters"},
    "exp_search":          {"vi": "Tim theo ten khach/HD/sale", "en": "Search customer/contract/sale"},
    # KPI Competition
    "kpi_progress":        {"vi": "Tien do chu ky thi dua",    "en": "Competition Progress"},
    "kpi_leaderboard":     {"vi": "Bang xep hang",              "en": "Leaderboard"},
    "kpi_all":             {"vi": "Tat ca",                     "en": "All"},
    "kpi_days_passed":     {"vi": "Ngay da qua",               "en": "Days Passed"},
    "kpi_days_left":       {"vi": "Ngay con lai",               "en": "Days Left"},
    "kpi_months_passed":   {"vi": "Thang da qua",               "en": "Months Passed"},
    "kpi_progress_pct":    {"vi": "Tien do",                    "en": "Progress"},
    # Misc
    "no_data":             {"vi": "Khong co du lieu phu hop.",  "en": "No data matches filter."},
    "month":               {"vi": "Thang",                      "en": "Month"},
    "revenue_vnd":         {"vi": "Doanh thu (VND)",            "en": "Revenue (VND)"},
}

def get_lang() -> str:
    return st.session_state.get("_app_lang", "vi")

def set_lang(lang: str) -> None:
    st.session_state["_app_lang"] = lang

def t(key: str) -> str:
    lang = get_lang()
    entry = _LOCALE.get(key)
    if entry:
        return entry.get(lang, entry.get("vi", key))
    return key

def render_logo() -> None:
    try:
        logo_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="48" viewBox="0 0 180 48"><defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#E85BD8"/><stop offset="100%" style="stop-color:#8B6FC9"/></linearGradient></defs><text x="8" y="30" font-family="Arial,Helvetica,sans-serif" font-size="28" font-weight="800" letter-spacing="4" fill="url(#g)">AFFINA</text><text x="8" y="44" font-family="Arial,Helvetica,sans-serif" font-size="9" fill="#7D5BA6" letter-spacing="0.5">Sales Dashboard</text></svg>'
        st.logo(logo_svg, size="large", link="https://affina.com.vn")
    except Exception:
        st.sidebar.markdown(
            "<div style='text-align:center;padding:8px 0;'>"
            "<span style='font-size:24px;font-weight:800;letter-spacing:3px;"
            "background:linear-gradient(135deg,#E85BD8,#8B6FC9);"
            "-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>"
            "AFFINA</span><br>"
            "<span style='font-size:10px;color:#7D5BA6;'>Sales Dashboard</span></div>",
            unsafe_allow_html=True,
        )

def render_lang_switch() -> None:
    lang = get_lang()
    st.sidebar.markdown("")
    if lang == "vi":
        col1, col2 = st.sidebar.columns([1, 1])
        with col1:
            st.markdown(
                "<div style='text-align:center;padding:6px;background:#E85BD8;border-radius:6px;"
                "color:white;font-weight:600;font-size:13px;'>VI</div>",
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("EN", key="_lang_en", use_container_width=True):
                set_lang("en")
                st.rerun()
    else:
        col1, col2 = st.sidebar.columns([1, 1])
        with col1:
            if st.button("VI", key="_lang_vi", use_container_width=True):
                set_lang("vi")
                st.rerun()
        with col2:
            st.markdown(
                "<div style='text-align:center;padding:6px;background:#E85BD8;border-radius:6px;"
                "color:white;font-weight:600;font-size:13px;'>EN</div>",
                unsafe_allow_html=True,
            )
