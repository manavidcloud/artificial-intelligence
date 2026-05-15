"""Authentication module for FinOps Dashboard."""
import os
import logging
from pathlib import Path

import bcrypt
import streamlit as st
import yaml

logger = logging.getLogger(__name__)

_USERS_FILE = Path(__file__).parent / "users.yaml"

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

LOGIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Hide Streamlit chrome on login page */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stSidebar"],
[data-testid="stDecoration"],
[data-testid="collapsedControl"],
.viewerBadge_container__r5tak { display: none !important; }

html, body, [data-testid="stApp"] {
    font-family: 'Inter', sans-serif !important;
    background: #020817 !important;
    margin: 0; padding: 0;
}

/* Animated background orbs */
[data-testid="stApp"]::before {
    content: '';
    position: fixed;
    top: -30%;
    left: -20%;
    width: 60%;
    height: 60%;
    background: radial-gradient(ellipse, rgba(0,120,212,0.18) 0%, transparent 70%);
    border-radius: 50%;
    animation: orb1 8s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}
[data-testid="stApp"]::after {
    content: '';
    position: fixed;
    bottom: -20%;
    right: -15%;
    width: 55%;
    height: 55%;
    background: radial-gradient(ellipse, rgba(96,165,250,0.12) 0%, transparent 70%);
    border-radius: 50%;
    animation: orb2 10s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}
@keyframes orb1 {
    from { transform: translate(0, 0) scale(1); }
    to   { transform: translate(6%, 8%) scale(1.15); }
}
@keyframes orb2 {
    from { transform: translate(0, 0) scale(1); }
    to   { transform: translate(-5%, -6%) scale(1.1); }
}

/* Center the main content block */
[data-testid="stMain"] > div {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    position: relative;
    z-index: 1;
}

/* Glassmorphism card */
.login-card {
    background: rgba(13,21,38,0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 44px 48px 48px;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04) inset;
    position: relative;
    overflow: hidden;
}
/* Top gradient border line */
.login-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #0078D4 0%, #60a5fa 50%, #38bdf8 100%);
    border-radius: 20px 20px 0 0;
}

.login-logo {
    text-align: center;
    margin-bottom: 8px;
    font-size: 42px;
    line-height: 1;
}
.login-title {
    text-align: center;
    color: #f1f5f9;
    font-size: 22px;
    font-weight: 700;
    margin: 0 0 4px;
    letter-spacing: -0.02em;
}
.login-subtitle {
    text-align: center;
    color: #64748b;
    font-size: 13px;
    margin: 0 0 32px;
}
.login-label {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 6px;
    display: block;
}

/* Override Streamlit inputs inside card */
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(0,120,212,0.6) !important;
    box-shadow: 0 0 0 3px rgba(0,120,212,0.12) !important;
}
.stTextInput > label { color: #94a3b8 !important; font-size: 12px !important; font-weight: 500 !important; letter-spacing: 0.05em; text-transform: uppercase; }

/* Sign-in button */
.stButton > button {
    background: linear-gradient(135deg, #0078D4 0%, #005a9e 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    letter-spacing: 0.02em;
    padding: 10px 0 !important;
    width: 100%;
    transition: opacity 0.2s, transform 0.15s;
    box-shadow: 0 4px 20px rgba(0,120,212,0.35);
}
.stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px); }

.sso-divider {
    display: flex; align-items: center; gap: 12px;
    color: #334155; font-size: 12px; margin: 20px 0;
}
.sso-divider::before, .sso-divider::after {
    content: ''; flex: 1;
    height: 1px; background: rgba(255,255,255,0.06);
}

.sso-btn {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px; padding: 10px 16px;
    color: #cbd5e1; font-size: 13px; font-weight: 500;
    cursor: pointer; width: 100%; text-align: center;
    transition: background 0.2s, border-color 0.2s;
}
.sso-btn:hover { background: rgba(0,120,212,0.12); border-color: rgba(0,120,212,0.3); }

.login-footer {
    text-align: center;
    color: #334155;
    font-size: 11px;
    margin-top: 28px;
}
[data-testid="stAlert"] { border-radius: 10px !important; }
</style>"""

SIDEBAR_USER_CSS = """<style>
.user-chip {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 8px;
}
.user-avatar {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #0078D4, #60a5fa);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 700; font-size: 12px;
    flex-shrink: 0;
}
.user-name { color: #e2e8f0; font-size: 13px; font-weight: 600; line-height: 1.2; }
.user-role { color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }
</style>"""


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------

def _load_users() -> dict:
    if not _USERS_FILE.exists():
        return {}
    with open(_USERS_FILE, "r") as f:
        data = yaml.safe_load(f) or {}
    return data.get("users", {})


def _save_users(users: dict) -> None:
    with open(_USERS_FILE, "w") as f:
        yaml.dump({"users": users}, f, default_flow_style=False)


def _verify(username: str, password: str) -> dict | None:
    """Verify credentials. Auto-hashes plaintext passwords on first use."""
    users = _load_users()
    user = users.get(username)
    if not user:
        return None

    stored = user.get("password", "")

    # Already a bcrypt hash
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        if bcrypt.checkpw(password.encode(), stored.encode()):
            return user
        return None

    # Plaintext — verify then upgrade in place
    if stored == password:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        users[username]["password"] = hashed
        try:
            _save_users(users)
        except Exception as exc:
            logger.warning("Could not persist hashed password: %s", exc)
        return user

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def require_auth() -> None:
    """Show login wall if the user is not authenticated. Calls st.stop() on failure."""
    if st.session_state.get("_user"):
        return

    st.markdown(LOGIN_CSS, unsafe_allow_html=True)

    # Centre the card using columns
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-logo">⚡</div>', unsafe_allow_html=True)
        st.markdown('<p class="login-title">FinOps Platform</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="login-subtitle">Azure Cost Intelligence Dashboard</p>',
            unsafe_allow_html=True,
        )

        username = st.text_input("Username", key="_login_user", placeholder="Enter username")
        password = st.text_input(
            "Password", type="password", key="_login_pass", placeholder="Enter password"
        )

        if st.button("Sign In", use_container_width=True):
            user = _verify(username.strip(), password)
            if user:
                st.session_state["_user"] = {"username": username.strip(), **user}
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

        st.markdown(
            '<div class="sso-divider">or continue with</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div class="sso-btn">
                <svg width="18" height="18" viewBox="0 0 48 48">
                  <path fill="#4285F4" d="M43.6 20H24v8h11.3C33.8 33.4 29.4 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6.5 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20c11 0 19.7-8 19.7-20 0-1.3-.1-2.7-.1-4z"/>
                </svg>
                Sign in with Azure AD / Google
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="login-footer">FinOps Platform v1.0 &nbsp;&bull;&nbsp; '
            'Secured by Workload Identity</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


def sidebar_user() -> None:
    """Render user chip and logout button in the sidebar."""
    user = st.session_state.get("_user", {})
    if not user:
        return

    st.markdown(SIDEBAR_USER_CSS, unsafe_allow_html=True)
    name = user.get("name", user.get("username", "User"))
    role = user.get("role", "viewer")
    initials = "".join(p[0].upper() for p in name.split()[:2])

    st.sidebar.markdown(
        f"""<div class="user-chip">
            <div class="user-avatar">{initials}</div>
            <div>
                <div class="user-name">{name}</div>
                <div class="user-role">{role}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Logout", use_container_width=True, key="_logout_btn"):
        st.session_state.clear()
        st.rerun()


def is_admin() -> bool:
    user = st.session_state.get("_user", {})
    return user.get("role") == "admin"


def current_user() -> dict:
    return st.session_state.get("_user", {})
