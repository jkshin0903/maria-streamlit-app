# -*- coding: utf-8 -*-
"""Shared application bootstrap for both the English and Korean entry points."""
import streamlit as st

from lib import ui
from lib.i18n import t, set_lang, get_lang

LANG_LABELS = {"en": "English", "ko": "한국어"}


def run(default_lang="en"):
    st.set_page_config(
        page_title="R&S Asset Management",
        page_icon="🎰",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "lang" not in st.session_state:
        st.session_state["lang"] = default_lang
    if "user" not in st.session_state:
        st.session_state["user"] = "Marge Brooks"

    ui.inject_css()

    # ---------------- sidebar ----------------
    with st.sidebar:
        st.markdown("### 🎰 R&S Asset Mgmt")
        st.caption(t("app.subtitle"))
        st.markdown("---")
        lang = st.radio(
            t("app.language"), options=["en", "ko"],
            format_func=lambda x: LANG_LABELS[x],
            index=["en", "ko"].index(get_lang()), horizontal=True,
        )
        if lang != get_lang():
            set_lang(lang)
            st.rerun()
        st.markdown("---")
        st.markdown(f"**👤 {t('app.session')}**")
        user = st.selectbox(
            t("app.signed_in"), list(ui.USERS.keys()),
            index=list(ui.USERS.keys()).index(st.session_state["user"]),
            label_visibility="collapsed",
        )
        if user != st.session_state["user"]:
            st.session_state["user"] = user
            st.rerun()
        st.caption(ui.current_role())
        st.markdown("---")

    scope = ui.user_scope().get("scope", "all")

    from screens import (po_entry, move_order, rpt_installed,
                         rpt_purchases, rpt_profitability)

    input_pages = [
        st.Page(po_entry.render, title=t("nav.po"),
                icon=":material/receipt_long:", url_path="po-entry"),
        st.Page(move_order.render, title=t("nav.move"),
                icon=":material/swap_horiz:", url_path="move-order"),
    ]
    report_pages = [
        st.Page(rpt_installed.render, title=t("nav.rpt1"),
                icon=":material/inventory_2:", url_path="rpt-installed", default=True),
        st.Page(rpt_purchases.render, title=t("nav.rpt2"),
                icon=":material/account_balance:", url_path="rpt-purchases"),
        st.Page(rpt_profitability.render, title=t("nav.rpt3"),
                icon=":material/insights:", url_path="rpt-profitability"),
    ]

    if scope == "reports":
        nav = st.navigation({t("nav.reports"): report_pages})
    elif scope == "site":
        nav = st.navigation({
            t("nav.input"): [input_pages[1]],
            t("nav.reports"): report_pages,
        })
    else:
        nav = st.navigation({
            t("nav.input"): input_pages,
            t("nav.reports"): report_pages,
        })

    nav.run()
