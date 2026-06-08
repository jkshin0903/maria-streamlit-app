# -*- coding: utf-8 -*-
"""Shared UI helpers, theming, and the simulated user directory."""
import streamlit as st

from lib.i18n import t, get_lang

# Simulated login directory (role-based access control)
# role: (English, Korean)
USERS = {
    "Marge Brooks": {
        "role": ("Business Operations Manager", "사업운영 매니저"),
        "scope": "all", "locations": None,
    },
    "Reid Lewis": {
        "role": ("President", "대표 (President)"),
        "scope": "all", "locations": None,
    },
    "Mike Anderson": {
        "role": ("Site Manager — Lafayette", "사이트 매니저 — Lafayette"),
        "scope": "site", "locations": [3, 4],
    },
    "Mark Davis": {
        "role": ("Site Manager — Fort Wayne", "사이트 매니저 — Fort Wayne"),
        "scope": "site", "locations": [5, 6],
    },
    "Foster Reed": {
        "role": ("Site Manager — Rensselaer", "사이트 매니저 — Rensselaer"),
        "scope": "site", "locations": [7, 8],
    },
    "Sandra Cole (CPA)": {
        "role": ("External Accountant", "외부 회계사 (CPA)"),
        "scope": "reports", "locations": None,
    },
}


def money(v):
    if v is None:
        return "—"
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def sn(serial):
    """Format a machine serial number as the SN-xxxxxxxxx label."""
    return f"SN-{serial}" if serial is not None else "—"


def current_user():
    return st.session_state.get("user", "Marge Brooks")


def current_role():
    role = USERS.get(current_user(), {}).get("role", "")
    if isinstance(role, tuple):
        return role[0] if get_lang() == "en" else role[1]
    return role


def user_scope():
    return USERS.get(current_user(), {})


def inject_css():
    st.markdown(
        """
        <style>
        :root { --rs-primary:#0F2A4A; --rs-accent:#C8102E; --rs-gold:#E0A800; }

        /* page width + base font */
        .block-container { padding-top: 3.6rem; padding-bottom: 3rem; max-width: 1400px; }
        html, body, [class*="css"] { font-family: "Segoe UI", Inter, system-ui, sans-serif; }

        /* keep Streamlit's floating top header from covering the app bar */
        header[data-testid="stHeader"] { background: transparent; }
        header[data-testid="stHeader"]::before { content:none; }

        /* sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg,#0F2A4A 0%,#163961 100%);
        }
        section[data-testid="stSidebar"] * { color:#E8EEF6 !important; }
        section[data-testid="stSidebar"] .stRadio label { color:#E8EEF6 !important; }

        /* app header bar */
        .rs-appbar {
            background: linear-gradient(90deg,#0F2A4A 0%,#1d4e86 100%);
            color:#fff; padding:16px 26px; border-radius:14px; margin-bottom:18px;
            box-shadow:0 6px 22px rgba(15,42,74,.25);
            display:flex; align-items:center; justify-content:space-between;
            flex-wrap:wrap; gap:8px 20px; overflow:visible;
        }
        .rs-appbar .brand { font-size:1.4rem; font-weight:700; letter-spacing:.3px;
            line-height:1.25; min-width:0; }
        .rs-appbar .brand small { display:block; font-size:.7rem; font-weight:400;
            opacity:.82; letter-spacing:1.2px; text-transform:uppercase;
            white-space:normal; }
        .rs-appbar .who { text-align:right; font-size:.85rem; line-height:1.4;
            white-space:nowrap; }
        .rs-appbar .who b { font-size:.98rem; }
        .rs-chip { display:inline-block; background:rgba(255,255,255,.16);
            padding:3px 10px; border-radius:20px; font-size:.72rem; margin-top:4px; }

        /* screen title */
        .rs-screen-code { color:var(--rs-accent); font-weight:700; letter-spacing:1px;
            font-size:.78rem; }
        .rs-screen-title { font-size:1.6rem; font-weight:700; color:var(--rs-primary);
            margin:0 0 2px 0; }
        .rs-screen-sub { color:#5a6b7d; font-size:.9rem; margin-bottom:6px; }

        /* first-time-user intro note */
        .rs-intro { background:#e8f6ec; border:1px solid #b7e2c4;
            border-left:4px solid #2e9e54; border-radius:10px; color:#1f5130;
            padding:12px 16px; margin:4px 0 12px 0; font-size:.9rem; line-height:1.5; }
        .rs-intro-title { font-weight:700; color:#14622f; font-size:.96rem;
            padding-bottom:6px; margin-bottom:8px; border-bottom:1px solid #c4e6cf; }
        .rs-intro ul { margin:0; padding-left:18px; }
        .rs-intro li { margin:3px 0; }

        /* section card */
        .rs-section { font-size:1rem; font-weight:700; color:var(--rs-primary);
            border-left:4px solid var(--rs-accent); padding-left:10px; margin:8px 0 6px 0; }

        /* metric tiles */
        div[data-testid="stMetric"] {
            background:#fff; border:1px solid #e7ecf2; border-radius:12px;
            padding:14px 16px; box-shadow:0 2px 8px rgba(15,42,74,.06);
        }
        div[data-testid="stMetricValue"] { color:var(--rs-primary); }

        /* buttons */
        .stButton>button, .stDownloadButton>button {
            border-radius:9px; font-weight:600; border:1px solid #cfd8e3;
        }
        .stButton>button[kind="primary"], .stDownloadButton>button {
            background:var(--rs-primary); border-color:var(--rs-primary); color:#fff;
        }
        .stButton>button[kind="primary"]:hover, .stDownloadButton>button:hover {
            background:#163961; border-color:#163961; color:#fff;
        }

        /* dataframe header */
        thead tr th { background:#eef3f9 !important; color:#0F2A4A !important;
            font-weight:700 !important; }

        /* status pills via markdown */
        .pill { padding:2px 10px; border-radius:20px; font-size:.75rem; font-weight:600; }
        .pill-green { background:#e3f6e9; color:#157347; }
        .pill-amber { background:#fff4d6; color:#9a6700; }
        .pill-red   { background:#fde2e4; color:#b3261e; }
        .pill-grey  { background:#eceff3; color:#566; }
        hr { margin:.6rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def appbar():
    user = current_user()
    role = current_role()
    st.markdown(
        f"""
        <div class="rs-appbar">
          <div class="brand">R&amp;S Entertainment Services
            <small>{t('app.brand_sub')}</small></div>
          <div class="who">{t('app.signed_in')} <b>{user}</b><br>
            <span class="rs-chip">{role}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def screen_header(code, title, subtitle=""):
    st.markdown(f'<div class="rs-screen-code">{code}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rs-screen-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="rs-screen-sub">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)


def intro(text):
    """Short 'what is this screen' note for first-time users, under the header."""
    st.markdown(f'<div class="rs-intro">{text}</div>', unsafe_allow_html=True)


def section(title):
    st.markdown(f'<div class="rs-section">{title}</div>', unsafe_allow_html=True)


def status_pill(value):
    m = {
        "Active": "pill-green", "Received": "pill-green", "Paid": "pill-green",
        "Completed": "pill-green", "Pending": "pill-amber",
        "Under Repair": "pill-amber", "In Warehouse": "pill-grey",
        "Cancelled": "pill-red", "Disposed": "pill-red",
    }
    cls = m.get(value, "pill-grey")
    label = t(f"st.{value}")
    return f'<span class="pill {cls}">{label}</span>'
