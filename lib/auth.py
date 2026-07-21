"""
lib/auth.py — Hệ thống xác thực password cho dashboard

Passwords đọc từ st.secrets (Streamlit Cloud → App settings → Secrets).
Fallback về defaults CHỈ cho local dev — production PHẢI dùng secrets.

Cách dùng trong mỗi page:
    from lib.auth import require_auth
    require_auth("kenh")          # sẽ block nếu chưa nhập đúng password
    # ... code trang bên dưới chỉ chạy nếu đã unlock
"""
from __future__ import annotations

import streamlit as st


# ============================================================================
# PASSWORD CONFIG — đọc từ st.secrets, fallback cho local dev
# ============================================================================
def _get_passwords() -> dict[str, str]:
    """Load page passwords từ st.secrets["passwords"]."""
    try:
        return dict(st.secrets["passwords"])
    except Exception:
        return {}


def _get_admin_password() -> str:
    """Load admin password từ st.secrets["admin_password"]."""
    try:
        return st.secrets["admin_password"]
    except Exception:
        return ""


# ============================================================================
# AUTH FUNCTIONS
# ============================================================================
def is_admin() -> bool:
    return st.session_state.get("_admin_unlocked", False)


def is_page_unlocked(page_key: str) -> bool:
    if is_admin():
        return True
    return st.session_state.get(f"_unlocked_{page_key}", False)


def _unlock_admin() -> None:
    st.session_state["_admin_unlocked"] = True


def _unlock_page(page_key: str) -> None:
    st.session_state[f"_unlocked_{page_key}"] = True


def require_auth(page_key: str, page_title: str = "") -> None:
    """Gọi ở đầu mỗi page. Nếu chưa unlock → hiện form password rồi st.stop()."""
    if is_page_unlocked(page_key):
        return

    admin_pwd = _get_admin_password()
    page_passwords = _get_passwords()

    if not admin_pwd and not page_passwords:
        st.warning(
            "Chưa cấu hình passwords trong st.secrets. "
            "Vào Streamlit Cloud → App settings → Secrets để thêm [passwords] và admin_password."
        )
        st.stop()

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
            elif admin_pwd and pwd == admin_pwd:
                _unlock_admin()
                st.rerun()
            elif pwd == page_passwords.get(page_key):
                _unlock_page(page_key)
                st.rerun()
            else:
                st.error("Sai mật khẩu. Thử lại hoặc liên hệ admin.")

        st.caption(
            "Admin: nhập mật khẩu admin để mở khóa tất cả trang."
        )

    st.stop()
