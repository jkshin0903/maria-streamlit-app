# -*- coding: utf-8 -*-
"""SCR-RPT-03 | Machine Profitability & Repair History Analysis (free report)."""
from datetime import date

import pandas as pd
import streamlit as st

from lib import db, ui, export
from lib.i18n import t

PERIODS = ["This Year", "This Half", "This Quarter", "This Month", "Custom"]
PERIOD_KEY = {"This Year": "r3.p_year", "This Half": "r3.p_half",
              "This Quarter": "r3.p_quarter", "This Month": "r3.p_month",
              "Custom": "r3.p_custom"}


def _period_range(label, custom):
    today = date.today()
    if label == "This Month":
        return date(today.year, today.month, 1), today
    if label == "This Quarter":
        q = (today.month - 1) // 3
        return date(today.year, q * 3 + 1, 1), today
    if label == "This Half":
        start_m = 1 if today.month <= 6 else 7
        return date(today.year, start_m, 1), today
    if label == "This Year":
        return date(today.year, 1, 1), today
    if label == "Custom" and isinstance(custom, (tuple, list)) and len(custom) == 2:
        return custom[0], custom[1]
    return date(today.year, 1, 1), today


def render():
    ui.appbar()
    ui.screen_header("SCR-RPT-03", t("r3.title"), t("r3.sub"))

    scope = ui.user_scope()
    sites = db.get_sites()
    types = db.get_machine_types()
    allowed = scope.get("locations")
    if allowed is not None:
        sites = sites[sites.location_id.isin(allowed)]
    loc_opts = {int(r.location_id): r.location_name for r in sites.itertuples()}

    ui.section(t("r3.sec_filter"))
    f1, f2, f3 = st.columns(3)
    with f1:
        period = st.selectbox(t("r3.f_period"), PERIODS,
                              format_func=lambda x: t(PERIOD_KEY[x]))
    with f2:
        custom = st.date_input(t("r3.f_custom"), value=(), format="MM/DD/YYYY",
                               disabled=(period != "Custom"))
    with f3:
        threshold = st.number_input(t("r3.f_threshold"), min_value=0.0, value=5000.0,
                                    step=500.0, help=t("r3.f_threshold_help"))
    f4, f5 = st.columns(2)
    with f4:
        sel_locs = st.multiselect(t("r3.f_loc"), options=list(loc_opts.keys()),
                                  format_func=lambda x: loc_opts[x],
                                  placeholder=t("word.all_locations"))
    with f5:
        sel_types = st.multiselect(t("r3.f_type"), options=types,
                                   placeholder=t("word.all_types"))

    b1, _ = st.columns([1, 5])
    search = b1.button(t("btn.search"), type="primary", width='stretch')
    if "rpt03_run" not in st.session_state:
        st.session_state.rpt03_run = True
    if search:
        st.session_state.rpt03_run = True
    if not st.session_state.rpt03_run:
        return

    start, end = _period_range(period, custom)
    st.caption(t("r3.window", a=f"{start:%m/%d/%Y}", b=f"{end:%m/%d/%Y}"))

    where = ["bl.location_type='Site'", "m.machine_status IN ('Active','Under Repair')"]
    params = []
    if allowed is not None:
        where.append("m.location_id IN (%s)" % ",".join(["%s"] * len(allowed)))
        params += allowed
    if sel_locs:
        where.append("m.location_id IN (%s)" % ",".join(["%s"] * len(sel_locs)))
        params += sel_locs
    if sel_types:
        where.append("m.machine_type IN (%s)" % ",".join(["%s"] * len(sel_types)))
        params += sel_types

    base = db.query_df(f"""
        SELECT m.serial_number, m.machine_name, m.manufacturer, m.machine_type,
               m.installation_date, m.machine_status, m.location_id,
               bl.location_name, c.revenue_share_pct
        FROM machine m
        JOIN business_location bl ON bl.location_id=m.location_id
        LEFT JOIN contract c ON c.location_id=bl.location_id AND c.contract_status='Active'
        WHERE {' AND '.join(where)}
        ORDER BY bl.location_name, m.machine_type
    """, params)

    if base.empty:
        st.info(t("r3.no_data"))
        return

    rows = []
    data_short = False
    for r in base.itertuples():
        rev = db.query_one(
            "SELECT COALESCE(SUM(amount),0) AS s FROM machine_revenue "
            "WHERE serial_number=%s AND revenue_month BETWEEN %s AND %s",
            (r.serial_number, start.strftime("%Y-%m-01"), end.strftime("%Y-%m-%d")))["s"]
        rev = float(rev or 0)
        rep = db.query_one(
            "SELECT COUNT(*) AS n, COALESCE(SUM(cost),0) AS c FROM machine_repair "
            "WHERE serial_number=%s", (r.serial_number,))
        rep_n, rep_cost = int(rep["n"]), float(rep["c"])
        share_pct = float(r.revenue_share_pct or 0)
        rs_share = rev * share_pct / 100.0

        inst = pd.to_datetime(r.installation_date) if r.installation_date is not None else None
        age_days = (date.today() - inst.date()).days if inst is not None else 0
        period_days = max(1, (end - max(start, inst.date())).days) if inst is not None else max(1, (end - start).days)
        rev_per_day = rev / period_days

        hist = db.query_df(
            """SELECT bl.location_name, h.start_date, h.end_date
               FROM machine_location_hst h JOIN business_location bl
               ON bl.location_id=h.location_id WHERE h.serial_number=%s
               ORDER BY h.start_date""", (r.serial_number,))
        if hist.empty:
            hist_str = r.location_name
        else:
            def _d(v):
                tt = pd.to_datetime(v)
                return f"{tt.month}/{tt.day}/{tt.strftime('%y')}"
            parts = []
            for hr in hist.itertuples():
                sd = _d(hr.start_date)
                ed = "present" if pd.isna(hr.end_date) else _d(hr.end_date)
                parts.append(f"{hr.location_name} ({sd}~{ed})")
            hist_str = " → ".join(parts)

        if age_days < 30:
            status, rec = "New", t("r3.rec_new")
        else:
            if rev < threshold:
                status = "Low"
            elif rev >= threshold * 2:
                status = "High"
            else:
                status = "Average"
            ratio = (rep_cost / rev) if rev > 0 else 999
            if ratio > 0.5:
                rec = t("r3.rec_junk")
            elif status == "Low":
                rec = t("r3.rec_relocate")
            elif rep_n >= 4:
                rec = t("r3.rec_replace")
            else:
                rec = t("r3.rec_keep")
        if inst is not None and age_days < 90:
            data_short = True

        rows.append(dict(
            Location=r.location_name, Machine=r.machine_name, Type=r.machine_type,
            SN=ui.sn(int(r.serial_number)),
            Installed=inst.strftime("%m/%d/%Y") if inst is not None else "—",
            Revenue=rev, RS_Share=rs_share, RevPerDay=rev_per_day,
            Repairs=rep_n, RepairCost=rep_cost, History=hist_str,
            Status=status, Recommendation=rec, _age=age_days))

    df = pd.DataFrame(rows)

    if data_short:
        st.warning(t("r3.data_short"))

    # ---------------- summary ----------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("r3.m_count"), len(df))
    m2.metric(t("r3.m_rev"), ui.money(df["Revenue"].sum()))
    m3.metric(t("r3.m_share"), ui.money(df["RS_Share"].sum()))
    m4.metric(t("r3.m_low"), int((df["Status"] == "Low").sum()))

    rec_counts = df["Recommendation"].value_counts()
    chips = "  ".join(f"<span class='pill pill-grey'>{k}: {v}</span>"
                      for k, v in rec_counts.items())
    st.markdown(chips, unsafe_allow_html=True)

    # column rename map (shared by export + view)
    rename = {
        "Location": t("r3.c_loc"), "Machine": t("r3.c_machine"), "Type": t("r3.c_type"),
        "SN": t("r3.c_sn"), "Installed": t("r3.c_installed"), "Revenue": t("r3.c_rev"),
        "RS_Share": t("r3.c_share"), "RevPerDay": t("r3.c_revday"),
        "Repairs": t("r3.c_repairs"), "RepairCost": t("r3.c_repaircost"),
        "History": t("r3.c_history"), "Status": t("c.status"),
        "Recommendation": t("r3.c_recommend")}

    exp = df.drop(columns=["_age"]).rename(columns=rename)
    e1, e2, _ = st.columns([1, 1, 4])
    e1.download_button(t("btn.export_report"),
                       export.to_excel_bytes(exp, "Profitability"),
                       file_name="profitability_analysis.xlsx", width='stretch')
    if e2.button(t("btn.print_pdf"), width='stretch'):
        st.toast(t("msg.exported"))
    st.markdown("---")

    # ---------------- styled table (red highlight for Low) ----------------
    view = df.drop(columns=["_age"]).copy()
    disp = view.rename(columns=rename)

    status_col = t("c.status")

    def hl(row):
        s = row[status_col]
        if s == "Low":
            return ["background-color:#fde2e4"] * len(row)
        if s == "High":
            return ["background-color:#e3f6e9"] * len(row)
        if s == "New":
            return ["background-color:#eef3f9"] * len(row)
        return [""] * len(row)

    styler = (disp.style
              .apply(hl, axis=1)
              .format({t("r3.c_rev"): "${:,.2f}", t("r3.c_share"): "${:,.2f}",
                       t("r3.c_revday"): "${:,.2f}", t("r3.c_repaircost"): "${:,.2f}"}))
    st.dataframe(styler, hide_index=True, width='stretch')

    st.caption(t("r3.legend"))
