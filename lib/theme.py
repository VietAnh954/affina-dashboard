"""
lib/theme.py — Global CSS injection for professional UI
Call inject_css() at the top of every page (after set_page_config).
"""
import streamlit as st

def inject_css():
    """Inject professional CSS vào page hiện tại. Gọi 1 lần/page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header():
    st.markdown(
        """<div style="display:flex; align-items:center; gap:16px; margin-top:28px; margin-bottom:8px;">
            <div style="font-size:36px; font-weight:800; letter-spacing:4px; line-height:1.4;
                        color:#E85BD8;
                        background: linear-gradient(135deg, #E85BD8, #8B6FC9);
                        -webkit-background-clip: text; background-clip: text;
                        -webkit-text-fill-color: transparent;">
                AFFINA
            </div>
            <div>
                <div style="font-size:22px; font-weight:700; color:#3D2B4F; line-height:1.4;">Sales Dashboard</div>
                <div style="font-size:13px; color:#7D5BA6; margin-top:2px; line-height:1.4;">
                    Tram viec da kho, Bao hiem co Affina lo
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

_CSS = """
<style>
/* ================================================================
   AFFINA DASHBOARD — Professional Theme CSS
   Applied globally via lib/theme.py inject_css()
   ================================================================ */

/* --- ROOT VARIABLES --- */
:root {
    --brand-primary: #E85BD8;
    --brand-secondary: #8B6FC9;
    --brand-dark: #3D2B4F;
    --brand-light: #F9EBF7;
    --brand-bg: #FFFAFE;
    --accent-green: #5FBFA0;
    --accent-rose: #E8738F;
    --shadow-sm: 0 1px 3px rgba(61,43,79,0.08);
    --shadow-md: 0 4px 12px rgba(61,43,79,0.10);
    --shadow-lg: 0 8px 24px rgba(61,43,79,0.12);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
}

/* --- SIDEBAR --- */
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(232,91,216,0.1);
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.5rem;
}
/* Sidebar nav links */
[data-testid="stSidebarNavItems"] a {
    border-radius: var(--radius-sm);
    transition: background 0.2s;
}
[data-testid="stSidebarNavItems"] a:hover {
    background: rgba(232,91,216,0.08);
}
[data-testid="stSidebarNavItems"] a[aria-selected="true"] {
    background: rgba(232,91,216,0.12);
    border-left: 3px solid var(--brand-primary);
}

/* --- METRIC CARDS (KPI) --- */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(249,235,247,0.6), rgba(255,250,254,0.8));
    border: 1px solid rgba(232,91,216,0.12);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-md);
    border-color: rgba(232,91,216,0.25);
}
[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: var(--brand-dark) !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    color: #7D5BA6 !important;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
[data-testid="stMetricDelta"] svg {
    width: 12px; height: 12px;
}

/* --- SECTION HEADERS --- */
.stMarkdown h3 {
    color: var(--brand-dark);
    font-weight: 700;
    font-size: 1.2rem;
    padding-bottom: 8px;
    border-bottom: 2px solid rgba(232,91,216,0.15);
    margin-bottom: 16px;
}
.stMarkdown h1 {
    font-weight: 800;
    letter-spacing: -0.5px;
}

/* --- PLOTLY CHART CONTAINERS --- */
[data-testid="stPlotlyChart"] {
    background: white;
    border: 1px solid rgba(232,91,216,0.08);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
    padding: 4px;
    transition: box-shadow 0.2s;
}
[data-testid="stPlotlyChart"]:hover {
    box-shadow: var(--shadow-md);
}

/* --- DATAFRAME / TABLES --- */
[data-testid="stDataFrame"] {
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
}
[data-testid="stDataFrame"] thead th {
    background: linear-gradient(135deg, #F3E8F9, #EBD8F5) !important;
    color: var(--brand-dark) !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    padding: 10px 12px !important;
    border-bottom: 2px solid rgba(232,91,216,0.2) !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(249,235,247,0.4) !important;
}
[data-testid="stDataFrame"] tbody td {
    font-size: 0.85rem;
    padding: 8px 12px !important;
}

/* --- TABS --- */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 8px 20px !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    transition: all 0.2s;
}
button[data-baseweb="tab"]:hover {
    background: rgba(232,91,216,0.06);
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(232,91,216,0.1) !important;
    border-bottom: 2px solid var(--brand-primary) !important;
    color: var(--brand-dark) !important;
}

/* --- BUTTONS --- */
.stButton button {
    border-radius: var(--radius-sm);
    font-weight: 600;
    transition: all 0.2s;
    border: 1px solid rgba(232,91,216,0.2);
}
.stButton button:hover {
    box-shadow: var(--shadow-sm);
    transform: translateY(-1px);
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
    border: none;
    color: white;
}
.stButton button[kind="primary"]:hover {
    box-shadow: 0 4px 16px rgba(232,91,216,0.3);
}

/* --- DOWNLOAD BUTTON --- */
[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary)) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    padding: 8px 24px !important;
}
[data-testid="stDownloadButton"] button:hover {
    box-shadow: 0 4px 16px rgba(232,91,216,0.3) !important;
    transform: translateY(-1px);
}

/* --- EXPANDER --- */
[data-testid="stExpander"] {
    border: 1px solid rgba(232,91,216,0.12);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
}
[data-testid="stExpander"] summary {
    font-weight: 600;
}

/* --- ALERT BOXES --- */
[data-testid="stAlert"] {
    border-radius: var(--radius-sm);
    border-left: 4px solid var(--brand-primary);
}

/* --- DIVIDER --- */
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(232,91,216,0.15), transparent);
    margin: 24px 0;
}

/* --- MULTISELECT TAGS --- */
[data-baseweb="tag"] {
    background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary)) !important;
    border: none !important;
    border-radius: 6px !important;
}

/* --- INPUT FIELDS --- */
[data-baseweb="input"],
[data-baseweb="select"] > div:first-child {
    border-radius: var(--radius-sm) !important;
    border-color: rgba(232,91,216,0.2) !important;
    transition: border-color 0.2s;
}
[data-baseweb="input"]:focus-within,
[data-baseweb="select"]:focus-within > div:first-child {
    border-color: var(--brand-primary) !important;
    box-shadow: 0 0 0 2px rgba(232,91,216,0.1) !important;
}

/* --- RADIO BUTTONS --- */
[data-testid="stRadio"] label {
    transition: background 0.15s;
    border-radius: 6px;
    padding: 2px 6px;
}
[data-testid="stRadio"] label:hover {
    background: rgba(232,91,216,0.06);
}

/* --- PROGRESS BAR --- */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--brand-primary), var(--brand-secondary)) !important;
    border-radius: 4px;
}

/* --- CAPTION --- */
[data-testid="stCaptionContainer"] p {
    color: #9B8AA8;
    font-size: 0.78rem;
}

/* --- MAIN BLOCK PADDING --- */
.stMainBlockContainer {
    padding: 1rem 2rem 3rem 2rem;
}

/* --- SCROLLBAR (WebKit) --- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(232,91,216,0.2);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(232,91,216,0.4);
}

/* --- ANIMATION for page load --- */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.stMainBlockContainer > div {
    animation: fadeInUp 0.4s ease-out;
}

/* --- SPINNER --- */
[data-testid="stSpinner"] {
    color: var(--brand-primary) !important;
}
</style>
"""
