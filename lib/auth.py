"""
lib/auth.py — Role-based authentication with bcrypt

3 roles:
  admin — all pages, full PII access
  head  — most pages, masked PII
  sale  — basic pages, no PII

Secrets format (st.secrets / secrets.toml):

  [auth]
  session_timeout = 1800   # seconds, default 30 min

  [auth.users.admin1]
  password_hash = "$2b$12$..."
  role = "admin"
  display_name = "Admin"

  [auth.users.sale_abc]
  password_hash = "$2b$12$..."
  role = "sale"
  display_name = "Nguyen Van A"

Generate hash:  python scripts/generate_password_hash.py

Backward compatibility: if [auth] section missing, falls back to
old [passwords] + admin_password system.
"""
from __future__ import annotations

import time

import streamlit as st

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


# ============================================================================
# ROLE CONFIG
# ============================================================================
ROLE_PAGES = {
    "admin": "__all__",
    "head": [
        "home", "kenh", "sales", "time", "export",
        "headsale", "executive", "customer", "forecast", "kpi",
    ],
    "sale": [
        "home", "kenh", "sales", "time", "export", "kpi",
    ],
}

ROLE_PII = {
    "admin": "full",
    "head": "masked",
    "sale": "none",
}

DEFAULT_TIMEOUT = 1800  # 30 minutes


# ============================================================================
# INTERNAL — new auth system
# ============================================================================
def _get_auth_config() -> dict | None:
    try:
        auth = st.secrets.get("auth", None)
        if auth and "users" in auth:
            return dict(auth)
    except Exception:
        pass
    return None


def _get_session_timeout() -> int:
    auth = _get_auth_config()
    if auth:
        return int(auth.get("session_timeout", DEFAULT_TIMEOUT))
    return DEFAULT_TIMEOUT


def _verify_password(plain: str, hashed: str) -> bool:
    if not _HAS_BCRYPT:
        return plain == hashed
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return plain == hashed


def _authenticate_user(username: str, password: str) -> dict | None:
    auth = _get_auth_config()
    if not auth:
        return None
    users = auth.get("users", {})
    user = users.get(username)
    if not user:
        for uname, udata in users.items():
            if udata.get("display_name", "").lower() == username.lower():
                user = udata
                username = uname
                break
    if not user:
        return None
    pwd_hash = user.get("password_hash", "")
    if _verify_password(password, pwd_hash):
        return {
            "username": username,
            "role": user.get("role", "sale"),
            "display_name": user.get("display_name", username),
        }
    return None


def _login_new_system(page_key: str, page_title: str) -> None:
    st.markdown(
        "<div style='max-width:420px; margin:120px auto; text-align:center;'>"
        "<h2 style='color:#3D2B4F;'>Affina Dashboard</h2>"
        f"<p style='color:#7D5BA6; margin-bottom:24px;'>{page_title or 'Dang nhap'}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        username = st.text_input(
            "Ten dang nhap",
            placeholder="Username",
            key=f"_login_user_{page_key}",
        )
        password = st.text_input(
            "Mat khau",
            type="password",
            placeholder="Mat khau",
            key=f"_login_pwd_{page_key}",
        )

        if st.button("Dang nhap", use_container_width=True, key=f"_login_btn_{page_key}"):
            if not username or not password:
                st.warning("Vui long nhap ten dang nhap va mat khau.")
            else:
                user_info = _authenticate_user(username.strip(), password)
                if user_info:
                    st.session_state["_auth_user"] = user_info
                    st.session_state["_auth_time"] = time.time()
                    st.session_state["_auth_last_activity"] = time.time()
                    st.rerun()
                else:
                    st.error("Sai ten dang nhap hoac mat khau.")

    st.stop()


# ============================================================================
# INTERNAL — legacy auth (backward compat)
# ============================================================================
def _get_passwords() -> dict[str, str]:
    try:
        return dict(st.secrets["passwords"])
    except Exception:
        return {}


def _get_admin_password() -> str:
    try:
        return st.secrets["admin_password"]
    except Exception:
        return ""


def _login_legacy(page_key: str, page_title: str) -> None:
    admin_pwd = _get_admin_password()
    page_passwords = _get_passwords()

    if not admin_pwd and not page_passwords:
        st.warning(
            "Chua cau hinh passwords trong st.secrets. "
            "Vao Streamlit Cloud → App settings → Secrets de them [auth.users] "
            "hoac [passwords] + admin_password."
        )
        st.stop()

    st.markdown(
        "<div style='max-width:420px; margin:120px auto; text-align:center;'>"
        "<h2 style='color:#3D2B4F;'>Affina Dashboard</h2>"
        f"<p style='color:#7D5BA6; margin-bottom:24px;'>{page_title or 'Trang yeu cau mat khau'}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pwd = st.text_input(
            "Nhap mat khau",
            type="password",
            placeholder="Mat khau trang hoac admin",
            key=f"_pwd_input_{page_key}",
            label_visibility="collapsed",
        )

        if st.button("Xac nhan", use_container_width=True, key=f"_btn_{page_key}"):
            if not pwd:
                st.warning("Vui long nhap mat khau.")
            elif admin_pwd and pwd == admin_pwd:
                st.session_state["_auth_user"] = {
                    "username": "admin",
                    "role": "admin",
                    "display_name": "Admin",
                }
                st.session_state["_auth_time"] = time.time()
                st.session_state["_auth_last_activity"] = time.time()
                st.rerun()
            elif pwd == page_passwords.get(page_key):
                st.session_state["_auth_user"] = {
                    "username": f"page_{page_key}",
                    "role": "sale",
                    "display_name": f"User ({page_key})",
                }
                st.session_state["_auth_time"] = time.time()
                st.session_state["_auth_last_activity"] = time.time()
                st.session_state[f"_unlocked_{page_key}"] = True
                st.rerun()
            else:
                st.error("Sai mat khau. Thu lai hoac lien he admin.")

        st.caption("Admin: nhap mat khau admin de mo khoa tat ca trang.")

    st.stop()


# ============================================================================
# PUBLIC API
# ============================================================================
def get_current_user() -> dict | None:
    return st.session_state.get("_auth_user")


def get_role() -> str:
    user = get_current_user()
    if not user:
        return ""
    return user.get("role", "sale")


def is_admin() -> bool:
    return get_role() == "admin"


def get_pii_level() -> str:
    return ROLE_PII.get(get_role(), "none")


def _check_timeout() -> bool:
    last = st.session_state.get("_auth_last_activity", 0)
    timeout = _get_session_timeout()
    if time.time() - last > timeout:
        logout()
        return True
    st.session_state["_auth_last_activity"] = time.time()
    return False


def logout() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("_auth_") or key.startswith("_unlocked_") or key == "_admin_unlocked":
            del st.session_state[key]


def require_auth(page_key: str, page_title: str = "") -> None:
    if get_current_user():
        if _check_timeout():
            st.info("Phien dang nhap het han. Vui long dang nhap lai.")
        else:
            role = get_role()
            allowed = ROLE_PAGES.get(role, [])
            if allowed == "__all__" or page_key in allowed:
                return
            # Legacy per-page unlock
            if st.session_state.get(f"_unlocked_{page_key}"):
                return
            st.error(f"Ban khong co quyen truy cap trang nay (role: {role}).")
            st.stop()

    auth_config = _get_auth_config()
    if auth_config:
        _login_new_system(page_key, page_title)
    else:
        _login_legacy(page_key, page_title)


def render_user_info() -> None:
    user = get_current_user()
    if user:
        role_label = {"admin": "Admin", "head": "Head Sale", "sale": "Sale"}.get(
            user["role"], user["role"]
        )
        st.sidebar.markdown(f"**{user['display_name']}** ({role_label})")
        if st.sidebar.button("Dang xuat", key="_logout_btn"):
            logout()
            st.rerun()
