# -*- coding: utf-8 -*-
"""SCR-RPT-01 | Installed Machine Status Report."""
from datetime import date

import pandas as pd
import streamlit as st

from lib import db, ui, export
from lib.i18n import t

STATUSES = ["Active", "In Warehouse", "Under Repair", "Disposed"]


def render():
    ui.appbar()
    ui.screen_header("SCR-RPT-01", t("r1.title"), t("r1.sub"))
    ui.intro(t("r1.intro"))

    scope = ui.user_scope()
    sites = db.get_locations()
    types = db.get_machine_types()

    allowed = scope.get("locations")
    loc_df = sites if allowed is None else sites[sites.location_id.isin(allowed)]
    loc_opts = {int(r.location_id): r.location_name for r in loc_df.itertuples()}

    # ---------------- filter bar ----------------
    ui.section(t("r1.sec_filter"))
    f1, f2 = st.columns(2)
    with f1:
        sel_locs = st.multiselect(t("r1.f_loc"), options=list(loc_opts.keys()),
                                  format_func=lambda x: loc_opts[x],
                                  placeholder=t("word.all_locations"))
    with f2:
        sel_types = st.multiselect(t("r1.f_type"), options=types,
                                   placeholder=t("word.all_types"))
    f3, f4 = st.columns([2, 2])
    with f3:
        sel_status = st.multiselect(t("r1.f_status"), options=STATUSES, default=["Active"],
                                    format_func=lambda x: t(f"st.{x}"),
                                    help=t("r1.f_status_help"))
    with f4:
        dr = st.date_input(t("r1.f_daterange"), value=(), format="MM/DD/YYYY",
                           help=t("r1.f_daterange_help"))

    b1, b2, b3, _ = st.columns([1, 1, 1, 3])
    search = b1.button(t("btn.search"), type="primary", width='stretch')

    if "rpt01_run" not in st.session_state:
        st.session_state.rpt01_run = True
    if search:
        st.session_state.rpt01_run = True
    if not st.session_state.rpt01_run:
        return

    # ---------------- query ----------------
    where, params = ["m.machine_status IS NOT NULL"], []
    if allowed is not None:
        where.append("m.location_id IN (%s)" % ",".join(["%s"] * len(allowed)))
        params += allowed
    if sel_locs:
        where.append("m.location_id IN (%s)" % ",".join(["%s"] * len(sel_locs)))
        params += sel_locs
    if sel_types:
        where.append("m.machine_type IN (%s)" % ",".join(["%s"] * len(sel_types)))
        params += sel_types
    status_filter = sel_status or ["Active"]
    where.append("m.machine_status IN (%s)" % ",".join(["%s"] * len(status_filter)))
    params += status_filter
    if isinstance(dr, (tuple, list)) and len(dr) == 2:
        where.append("DATE(m.installation_date) BETWEEN %s AND %s")
        params += [dr[0].strftime("%Y-%m-%d"), dr[1].strftime("%Y-%m-%d")]

    sql = f"""
        SELECT bl.location_name, bl.address, bl.city, bl.state,
               m.machine_type, m.machine_name, m.manufacturer, m.serial_number,
               m.purchase_date, m.purchase_price, m.installation_date,
               m.machine_status,
               (SELECT COUNT(*) FROM machine_repair r
                WHERE r.serial_number=m.serial_number) AS repair_count
        FROM machine m
        LEFT JOIN business_location bl ON bl.location_id=m.location_id
        WHERE {' AND '.join(where)}
        ORDER BY bl.location_name, m.machine_type, m.installation_date
    """
    df = db.query_df(sql, params)
    if df.empty:
        st.info(t("r1.no_data"))
        return

    # ---------------- summary metrics ----------------
    grand_total = float(df["purchase_price"].fillna(0).sum())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("r1.m_total"), len(df))
    m2.metric(t("r1.m_locs"), df["location_name"].nunique())
    m3.metric(t("r1.m_repairs"), int(df["repair_count"].sum()))
    m4.metric(t("r1.m_grand"), ui.money(grand_total))

    # ---------------- export / print ----------------
    exp = df.copy()
    exp["S/N"] = exp["serial_number"].map(ui.sn)
    exp["machine_status"] = exp["machine_status"].map(lambda x: t(f"st.{x}"))
    exp_cols = exp[["location_name", "address", "machine_type", "machine_name",
                    "S/N", "manufacturer", "purchase_date", "purchase_price",
                    "installation_date", "machine_status", "repair_count"]]
    exp_cols.columns = [t("r1.f_loc"), t("c.address"), t("c.type"), t("c.machine"), "S/N",
                        t("c.manuf"), t("c.pdate"), t("c.pprice"), t("c.idate"),
                        t("c.status"), t("c.repairs")]
    e1, e2, _ = st.columns([1, 1, 4])
    e1.download_button(t("btn.export_excel"),
                       export.to_excel_bytes(exp_cols, "Installed Machines"),
                       file_name="installed_machine_status.xlsx", width='stretch')
    if e2.button(t("btn.print"), width='stretch'):
        st.toast(t("msg.printed_short"))

    st.markdown("---")

    # ---------------- grouped output (Location > Type) ----------------
    for loc, gloc in df.groupby("location_name", sort=False):
        addr = f"{gloc.iloc[0]['address']}, {gloc.iloc[0]['city']}, {gloc.iloc[0]['state']}"
        loc_subtotal = float(gloc["purchase_price"].fillna(0).sum())
        st.markdown(f"#### 🏢 {loc}")
        st.caption(f"📍 {addr}")
        for mtype, gtype in gloc.groupby("machine_type", sort=False):
            tdf = gtype.copy()
            tdf["S/N"] = tdf["serial_number"].map(ui.sn)
            tdf["machine_status"] = tdf["machine_status"].map(lambda x: t(f"st.{x}"))
            show = tdf[["machine_name", "manufacturer", "S/N", "purchase_date",
                        "purchase_price", "installation_date", "machine_status",
                        "repair_count"]].rename(columns={
                "machine_name": t("c.machine"), "manufacturer": t("c.manuf"),
                "purchase_date": t("c.pdate"), "purchase_price": t("c.pprice"),
                "installation_date": t("c.idate"),
                "machine_status": t("c.status"), "repair_count": t("c.repairs")})
            st.markdown(f"**▸ {mtype}**  ·  " + t("r1.units", n=len(gtype)))
            st.dataframe(
                show, hide_index=True, width='stretch',
                column_config={
                    t("c.pprice"): st.column_config.NumberColumn(format="$%.2f"),
                    t("c.pdate"): st.column_config.DatetimeColumn(format="MM/DD/YYYY"),
                    t("c.idate"): st.column_config.DatetimeColumn(format="MM/DD/YYYY"),
                })
        st.markdown(
            f"<div style='text-align:right;font-weight:700;color:#0F2A4A'>"
            f"{t('r1.subtotal', loc=loc, amt=ui.money(loc_subtotal), n=len(gloc))}</div>",
            unsafe_allow_html=True)
        st.markdown("---")

    st.markdown(
        f"<div style='text-align:right;font-size:1.1rem;font-weight:800;"
        f"color:#C8102E'>{t('r1.grand', n=len(df), amt=ui.money(grand_total))}</div>",
        unsafe_allow_html=True)
