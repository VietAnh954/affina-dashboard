"""
lib/auth.py — Hệ thống xác thực password cho dashboard

Mỗi trang có password riêng. Admin password mở khóa tất cả 1 lần.
Password lưu trong dict (production nên chuyển sang st.secrets hoặc env).

Cách dùng trong mỗi page:
    from lib.auth import require_auth
    require_auth("kenh")          # sẽ block nếu chưa nhập đúng password
    # ... code trang bên dưới chỉ chạy nếu đã unlock
"""
from __future__ import annotations

import streamlit as st

# ============================================================================
# PASSWORD CONFIG
# ============================================================================
# Key = page identifier, Value = password
# Thứ tự tương ứng các trang trong sidebar
PAGE_PASSWORDS: dict[str, str] = {
    "home":         "1111",   # Trang chủ - Tổng quan
    "kenh":         "2222",   # Kênh & Sản phẩm
    "sales":        "3333",   # Đội ngũ Sales
    "time":         "4444",   # Phân tích thời gian
    "export":       "5555",   # Chi tiết & Export
    "headsale":     "6666",   # Head Sale Dashboard
    "executive":    "7777",   # Executive Insights
    "customer":     "8888",   # Customer Analytics
    "forecast":     "9999",   # Forecast & Anomaly
    "kpi":          "1234",   # KPI Competition (trang mới)
}

# Admin password — nhập 1 lần, mở khóa TẤT CẢ trang
ADMIN_PASSWORD = "admin2026"


# ============================================================================
# AUTH FUNCTIONS
# ============================================================================
def is_admin() -> bool:
    """Kiểm tra admin đã login chưa."""
    return st.session_state.get("_admin_unlocked", False)


def is_page_unlocked(page_key: str) -> bool:
    """Kiểm tra 1 trang cụ thể đã unlock chưa."""
    if is_admin():
        return True
    return st.session_state.get(f"_unlocked_{page_key}", False)


def _unlock_admin() -> None:
    st.session_state["_admin_unlocked"] = True


def _unlock_page(page_key: str) -> None:
    st.session_state[f"_unlocked_{page_key}"] = True


def require_auth(page_key: str, page_title: str = "") -> None:
    """Gọi ở đầu mỗi page. Nếu chưa unlock → hiện form password rồi st.stop().
    Nếu đã unlock → return bình thường, code page tiếp tục chạy.

    Args:
        page_key:   key trong PAGE_PASSWORDS (VD: "kenh", "sales", "kpi")
        page_title: tên hiển thị trên form login (VD: "Kênh & Sản phẩm")
    """
    if is_page_unlocked(page_key):
        return  # đã unlock — page chạy tiếp

    # ── Hiển thị form login ──
    st.markdown(
        "<div style='max-width:420px; margin:120px auto; text-align:center;'>"
        "<h2 style='color:#3D2B4F;'>Affina Dashboard</h2>"
        f"<p style='color:#7D5BA6; margin-bottom:24px;'>{page_title or 'Trang yêu cầu mật khẩu'}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input(
            "Nhập mật khẩu",
            type="password",
            placeholder="Mật khẩu trang hoặc admin",
            key=f"_pwd_input_{page_key}",
            label_visibility="collapsed",
        )

        if st.button("Xác nhận", use_container_width=True, key=f"_btn_{page_key}"):
            if not pwd:
                st.warning("Vui lòng nhập mật khẩu.")
            elif pwd == ADMIN_PASSWORD:
                _unlock_admin()
                st.rerun()
            elif pwd == PAGE_PASSWORDS.get(page_key):
                _unlock_page(page_key)
                st.rerun()
            else:
                st.error("Sai mật khẩu. Thử lại hoặc liên hệ admin.")

        st.caption(
            "Admin: nhập mật khẩu admin để mở khóa tất cả trang."
        )

    st.stop()
