"""
lib/i18n.py — Internationalization system for Affina Dashboard
=================================================================
Usage:
    from lib.i18n import t, get_lang, set_lang, render_lang_switcher

    st.title(t("home_title"))
    st.metric(t("revenue"), fmt_vnd(total_rev, short=True))

All translatable strings are keyed here. To add a new string:
    1. Add key to both VI and EN dicts below
    2. Use t("your_key") in the page code
=================================================================
"""
from __future__ import annotations
import streamlit as st

# ============================================================================
# TRANSLATIONS
# ============================================================================
VI = {
    # ── Global / Sidebar ──
    "brand_tagline":           "Bao hiem · Suc khoe · Tai chinh",
    "brand_slogan":            "Tram viec da kho, Bao hiem co Affina lo",
    "filters":                 "Bo loc chung",
    "date_range":              "Khoang thoi gian",
    "source":                  "Source",
    "channel":                 "Channel",
    "insurance_type":          "Loai bao hiem",
    "insurer":                 "Nha bao hiem",
    "refresh":                 "Lam moi du lieu",
    "last_updated":            "Data cap nhat",
    "total_rows":              "Tong so dong",
    "switch_lang":             "Switch to English  (EN)",

    # ── Page titles ──
    "home_title":              "Affina Sales Dashboard",
    "home_subtitle":           "Buc tranh tong the doanh thu, san pham, kenh, doi ngu sale.",
    "kenh_title":              "Kenh & San pham",
    "sales_title":             "Doi ngu Sales",
    "time_title":              "Phan tich thoi gian",
    "export_title":            "Chi tiet & Export",
    "headsale_title":          "Head Sale Dashboard",
    "executive_title":         "Executive Insights",
    "customer_title":          "Customer Analytics",
    "forecast_title":          "Forecast & Anomaly",
    "kpi_title":               "KPI Competition — CLB Tinh Hoa Affina",

    # ── KPI Metrics ──
    "revenue":                 "Doanh thu truoc thue",
    "total_payment":           "Tong thanh toan",
    "contracts":               "So hop dong",
    "affina_revenue":          "Affina Revenue",
    "est_bonus":               "EST Bonus",
    "premium":                 "Phi BH (Premium)",
    "active_sales":            "Sale dang hoat dong",
    "avg_rev_contract":        "TB Doanh thu / HD",
    "vs_prev":                 "so ky truoc",

    # ── Section headers ──
    "key_metrics":             "Chi so kinh doanh chinh",
    "trends_structure":        "Xu huong & Co cau",
    "last_30_days":            "30 ngay gan nhat (trong khoang loc)",
    "top_10":                  "Top 10",
    "explore_more":            "Kham pha sau hon",
    "rev_by_month":            "Doanh thu theo thang (chia theo Source)",
    "rev_structure":           "Co cau doanh thu theo Source",
    "total_label":             "Tong DT",
    "avg_label":               "TB",

    # ── Tables ──
    "top_sale_revenue":        "Top 10 Sale theo Doanh thu",
    "top_insurer_revenue":     "Top 10 Nha bao hiem theo Doanh thu",
    "rank":                    "Hang",
    "name":                    "Ho ten",
    "revenue_col":             "Doanh thu",
    "n_contracts":             "So HD",

    # ── Chart labels ──
    "month":                   "Thang",
    "revenue_vnd":             "Doanh thu (VND)",
    "day":                     "Ngay",

    # ── Export ──
    "download":                "Tai xuong",
    "download_csv":            "Tai CSV (nhanh)",
    "download_excel":          "Tai Excel (format dep)",
    "generating_excel":        "Dang tao file Excel...",
    "export_builder":          "Export Builder — Xuat file Excel",
    "select_template":         "Chon template hoac custom cot",
    "template":                "Template",
    "file_structure":          "Cau truc file",
    "split_sheets":            "Chia thanh nhieu sheet?",
    "single_sheet":            "1 sheet (tat ca data)",
    "split_source":            "Split by Source (Core/Neo/TSA)",
    "split_type":              "Split by Loai BH (7 sheets)",
    "split_insurer":           "Split by Top 15 Nha BH",
    "add_summary":             "Them sheet Summary",
    "preview":                 "Preview (20 dong dau)",
    "advanced_filter":         "Bo loc nang cao (tuy chon)",
    "search_placeholder":      "VD: Nguyen, HD_000123...",
    "search_label":            "Tim theo ten khach/HD/sale",
    "amount_range":            "So tien thanh toan (VND)",
    "product":                 "San pham",
    "filter_result":           "Ket qua filter",

    # ── Sales page ──
    "top_20_sales":            "Top 20 Salesperson theo Doanh thu",
    "bdm_performance":         "Hieu suat BDM (Quan ly cap 1)",
    "bdd_performance":         "Hieu suat BDD (Quan ly cap 2)",
    "hierarchy":               "Cau truc nhanh: BDD — BDM — So sale & Doanh thu",
    "hierarchy_caption":       "Moi bar = 1 BDM, nhom theo BDD.",
    "rev_by_branch":           "Doanh thu theo nhanh",
    "sales_by_branch":         "So sale theo nhanh",
    "scatter_title":           "Scatter: So HD x Doanh thu / Sale",
    "scatter_caption":         "Goc phai-tren = star performer.",
    "detail_table":            "Bang chi tiet toan bo Sales",

    # ── Time analysis ──
    "yoy_comparison":          "So sanh cung ky (Year-over-Year)",
    "mom_growth":              "Tang truong theo thang (Month-over-Month)",
    "heatmap_dow":             "Heatmap: Thu trong tuan x Tuan trong nam",
    "cumulative_rev":          "Doanh thu cong don theo Source",
    "contract_expiry":         "Hop dong sap het han",

    # ── KPI Competition ──
    "kpi_period":              "Chu ky thi dua",
    "kpi_prize":               "Giai thuong: 13 suat du lich Trung Quoc",
    "kpi_announce":            "Cong bo: Thang 04/2027",
    "progress":                "Tien do chu ky thi dua",
    "days_elapsed":            "Ngay da qua",
    "days_remaining":          "Ngay con lai",
    "months_elapsed":          "Thang da qua",
    "progress_pct":            "Tien do",
    "leaderboard":             "Bang xep hang",
    "all":                     "Tat ca",
    "director":                "Giam Doc (Top 3)",
    "manager":                 "Truong Phong (Top 5)",
    "specialist":              "Chuyen Vien (Top 5)",
    "total_points":            "Tong diem",
    "base_points":             "Diem QD",
    "rank_bonus":              "Bonus rank",
    "months_top3":             "Thang top 3",
    "months_active":           "Thang active",
    "total_rev":               "Tong doanh thu",
    "gap_to_prize":            "Khoang cach den vung giai thuong",
    "cumulative_points":       "Tien trinh tich luy diem theo thang",
    "monthly_rank":            "Xep hang theo thang",
    "compare_1v1":             "So sanh 1 vs 1",
    "forecast_end":            "Du bao cuoi chu ky (uoc tinh)",
    "point_distribution":      "Phan phoi diem — Muc do canh tranh",

    # ── Head Sale ──
    "head_view":               "Head Sale View",
    "both_side":               "Ca 2 (side-by-side)",
    "compare_with":            "So sanh voi",
    "compare_off":             "Tat so sanh",
    "compare_month":           "Ky truoc (thang)",
    "compare_year":            "Cung ky nam truoc",

    # ── Executive ──
    "exec_summary":            "Tom tat dieu hanh",
    "wins":                    "Diem sang",
    "concerns":                "Diem can chu y",
    "growth_decomposition":    "Growth Decomposition — Vi sao doanh thu thay doi?",
    "statistical_kpi":         "KPI voi do tin cay thong ke (95% CI)",
    "correlation":             "Phan tich tuong quan",
    "percentile_rank":         "Percentile Rank",
    "recommendations":         "Khuyen nghi hanh dong (auto)",

    # ── Customer ──
    "customer_scale":          "Quy mo khach hang",
    "demographics":            "Demographics — Chan dung khach hang",
    "rfm_title":               "RFM Segmentation — Ai la khach VIP?",
    "cohort_title":            "Cohort Retention — Khach co quay lai mua khong?",
    "crosssell_title":         "Cross-sell Matrix",
    "addon_title":             "BHSK Add-on Attachment Rate",

    # ── Forecast ──
    "forecast_30d":            "Du bao doanh thu 30 ngay toi",
    "anomaly_title":           "Anomaly Detection — Ngay nao bat thuong?",
    "seasonal_title":          "Seasonal Decomposition",
    "dow_pattern":             "Pattern theo Thu trong tuan x Thang trong nam",
    "volatility":              "Volatility — Doanh thu on dinh hay bien dong?",

    # ── Auth ──
    "enter_password":          "Nhap mat khau",
    "confirm":                 "Xac nhan",
    "wrong_password":          "Sai mat khau. Thu lai hoac lien he admin.",
    "admin_hint":              "Admin: nhap mat khau admin de mo khoa tat ca trang.",

    # ── Misc ──
    "no_data":                 "Khong co du lieu phu hop voi bo loc hien tai.",
    "loading":                 "Dang tai du lieu...",
}

EN = {
    # ── Global / Sidebar ──
    "brand_tagline":           "Insurance · Health · Finance",
    "brand_slogan":            "Your trusted insurance partner",
    "filters":                 "Filters",
    "date_range":              "Date range",
    "source":                  "Source",
    "channel":                 "Channel",
    "insurance_type":          "Insurance type",
    "insurer":                 "Insurer",
    "refresh":                 "Refresh Data",
    "last_updated":            "Last updated",
    "total_rows":              "Total rows",
    "switch_lang":             "Tieng Viet  (VI)",

    # ── Page titles ──
    "home_title":              "Affina Sales Dashboard",
    "home_subtitle":           "Revenue overview, products, channels, and sales team.",
    "kenh_title":              "Channels & Products",
    "sales_title":             "Sales Team",
    "time_title":              "Time Analysis",
    "export_title":            "Details & Export",
    "headsale_title":          "Head Sale Dashboard",
    "executive_title":         "Executive Insights",
    "customer_title":          "Customer Analytics",
    "forecast_title":          "Forecast & Anomaly",
    "kpi_title":               "KPI Competition — Affina Elite Club",

    # ── KPI Metrics ──
    "revenue":                 "Pre-tax Revenue",
    "total_payment":           "Total Payment",
    "contracts":               "Contracts",
    "affina_revenue":          "Affina Revenue",
    "est_bonus":               "EST Bonus",
    "premium":                 "Insurance Premium",
    "active_sales":            "Active Sales",
    "avg_rev_contract":        "Avg Revenue / Contract",
    "vs_prev":                 "vs prev period",

    # ── Section headers ──
    "key_metrics":             "Key Business Metrics",
    "trends_structure":        "Trends & Structure",
    "last_30_days":            "Last 30 days (within filter range)",
    "top_10":                  "Top 10",
    "explore_more":            "Explore More",
    "rev_by_month":            "Monthly Revenue (by Source)",
    "rev_structure":           "Revenue Structure by Source",
    "total_label":             "Total",
    "avg_label":               "Avg",

    # ── Tables ──
    "top_sale_revenue":        "Top 10 Sales by Revenue",
    "top_insurer_revenue":     "Top 10 Insurers by Revenue",
    "rank":                    "Rank",
    "name":                    "Name",
    "revenue_col":             "Revenue",
    "n_contracts":             "Contracts",

    # ── Chart labels ──
    "month":                   "Month",
    "revenue_vnd":             "Revenue (VND)",
    "day":                     "Day",

    # ── Export ──
    "download":                "Download",
    "download_csv":            "Download CSV (fast)",
    "download_excel":          "Download Excel (formatted)",
    "generating_excel":        "Generating Excel file...",
    "export_builder":          "Export Builder",
    "select_template":         "Select template or custom columns",
    "template":                "Template",
    "file_structure":          "File structure",
    "split_sheets":            "Split into multiple sheets?",
    "single_sheet":            "1 sheet (all data)",
    "split_source":            "Split by Source (Core/Neo/TSA)",
    "split_type":              "Split by Insurance Type (7 sheets)",
    "split_insurer":           "Split by Top 15 Insurers",
    "add_summary":             "Add Summary sheet",
    "preview":                 "Preview (first 20 rows)",
    "advanced_filter":         "Advanced Filter (optional)",
    "search_placeholder":      "e.g. Nguyen, HD_000123...",
    "search_label":            "Search by customer/contract/sale",
    "amount_range":            "Payment amount (VND)",
    "product":                 "Product",
    "filter_result":           "Filter result",

    # ── Sales page ──
    "top_20_sales":            "Top 20 Salesperson by Revenue",
    "bdm_performance":         "BDM Performance (Level 1 Manager)",
    "bdd_performance":         "BDD Performance (Level 2 Manager)",
    "hierarchy":               "Branch Structure: BDD — BDM — Sales & Revenue",
    "hierarchy_caption":       "Each bar = 1 BDM, grouped by BDD.",
    "rev_by_branch":           "Revenue by branch",
    "sales_by_branch":         "Sales count by branch",
    "scatter_title":           "Scatter: Contracts x Revenue / Sale",
    "scatter_caption":         "Top-right = star performer.",
    "detail_table":            "Full Sales Detail Table",

    # ── Time analysis ──
    "yoy_comparison":          "Year-over-Year Comparison",
    "mom_growth":              "Month-over-Month Growth",
    "heatmap_dow":             "Heatmap: Day of Week x Week of Year",
    "cumulative_rev":          "Cumulative Revenue by Source",
    "contract_expiry":         "Expiring Contracts",

    # ── KPI Competition ──
    "kpi_period":              "Competition period",
    "kpi_prize":               "Prize: 13 trips to China",
    "kpi_announce":            "Results: April 2027",
    "progress":                "Competition Progress",
    "days_elapsed":            "Days elapsed",
    "days_remaining":          "Days remaining",
    "months_elapsed":          "Months elapsed",
    "progress_pct":            "Progress",
    "leaderboard":             "Leaderboard",
    "all":                     "All",
    "director":                "Director (Top 3)",
    "manager":                 "Manager (Top 5)",
    "specialist":              "Specialist (Top 5)",
    "total_points":            "Total points",
    "base_points":             "Base points",
    "rank_bonus":              "Rank bonus",
    "months_top3":             "Months in top 3",
    "months_active":           "Active months",
    "total_rev":               "Total revenue",
    "gap_to_prize":            "Gap to prize zone",
    "cumulative_points":       "Cumulative Points Progress",
    "monthly_rank":            "Monthly Rankings",
    "compare_1v1":             "Head-to-Head Comparison",
    "forecast_end":            "End-of-Cycle Forecast (estimate)",
    "point_distribution":      "Point Distribution — Competition Intensity",

    # ── Head Sale ──
    "head_view":               "Head Sale View",
    "both_side":               "Both (side-by-side)",
    "compare_with":            "Compare with",
    "compare_off":             "No comparison",
    "compare_month":           "Previous period (month)",
    "compare_year":            "Same period last year",

    # ── Executive ──
    "exec_summary":            "Executive Summary",
    "wins":                    "Top Wins",
    "concerns":                "Top Concerns",
    "growth_decomposition":    "Growth Decomposition — Why did revenue change?",
    "statistical_kpi":         "KPI with Statistical Confidence (95% CI)",
    "correlation":             "Correlation Analysis",
    "percentile_rank":         "Percentile Rank",
    "recommendations":         "Actionable Recommendations (auto)",

    # ── Customer ──
    "customer_scale":          "Customer Scale",
    "demographics":            "Demographics — Customer Profile",
    "rfm_title":               "RFM Segmentation — Who are VIP customers?",
    "cohort_title":            "Cohort Retention — Do customers return?",
    "crosssell_title":         "Cross-sell Matrix",
    "addon_title":             "Health Insurance Add-on Attachment Rate",

    # ── Forecast ──
    "forecast_30d":            "30-Day Revenue Forecast",
    "anomaly_title":           "Anomaly Detection — Which days are unusual?",
    "seasonal_title":          "Seasonal Decomposition",
    "dow_pattern":             "Day of Week x Month Pattern",
    "volatility":              "Volatility — Is revenue stable or volatile?",

    # ── Auth ──
    "enter_password":          "Enter password",
    "confirm":                 "Confirm",
    "wrong_password":          "Wrong password. Try again or contact admin.",
    "admin_hint":              "Admin: enter admin password to unlock all pages.",

    # ── Misc ──
    "no_data":                 "No data matches the current filter.",
    "loading":                 "Loading data...",
}

_DICTS = {"vi": VI, "en": EN}


# ============================================================================
# CORE FUNCTIONS
# ============================================================================
def get_lang() -> str:
    """Return current language code: 'vi' or 'en'."""
    return st.session_state.get("_app_lang", "vi")


def set_lang(lang: str) -> None:
    """Set language and trigger rerun."""
    st.session_state["_app_lang"] = lang


def t(key: str) -> str:
    """Translate a key to the current language.
    Falls back to key itself if not found (so untranslated keys show as-is).
    """
    lang = get_lang()
    d = _DICTS.get(lang, VI)
    return d.get(key, VI.get(key, key))


def render_lang_switcher() -> None:
    """Render language toggle button in sidebar with flag icons."""
    lang = get_lang()
    if lang == "vi":
        label = t("switch_lang")  # "Switch to English (EN)"
    else:
        label = t("switch_lang")  # "Tieng Viet (VI)"

    if st.sidebar.button(label, key="_lang_switch_btn", use_container_width=True):
        new_lang = "en" if lang == "vi" else "vi"
        set_lang(new_lang)
        st.rerun()
