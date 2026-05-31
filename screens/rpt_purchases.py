# -*- coding: utf-8 -*-
"""SCR-RPT-02 | Annual Purchased Product List Report."""
from datetime import date

import pandas as pd
import streamlit as st

from lib import db, ui, export
from lib.i18n import t

CURRENT_YEAR = 2026


def render():
    ui.appbar()
    ui.screen_header("SCR-RPT-02", t("r2.title"), t("r2.sub"))

    vendors = db.get_vendors()
    types = db.get_machine_types()

    ui.section(t("r1.sec_filter"))
    f1, f2, f3 = st.columns(3)
    with f1:
        years = list(range(CURRENT_YEAR, CURRENT_YEAR - 5, -1))
        year = st.selectbox(t("r2.f_year"), years, index=0)
    with f2:
        vopts = {0: t("word.all_vendors")}
        vopts.update({int(r.vendor_id): r.vendor_name for r in vendors.itertuples()})
        vid = st.selectbox(t("r2.f_vendor"), options=list(vopts.keys()),
                           format_func=lambda x: vopts[x])
    with f3:
        topts = [None] + types
        mtype = st.selectbox(t("r2.f_type"), topts,
                             format_func=lambda x: t("word.all_types") if x is None else x)
    f4, f5 = st.columns([2, 2])
    with f4:
        dr = st.date_input(t("r2.f_daterange", year=year), value=(), format="MM/DD/YYYY",
                           help=t("r2.f_daterange_help"))
    with f5:
        statuses = ["Received", "All", "Pending", "Cancelled"]
        po_status = st.radio(t("r2.f_status"), statuses, horizontal=True, index=0,
                             format_func=lambda x: t("word.all") if x == "All" else t(f"st.{x}"))

    b1, _ = st.columns([1, 5])
    search = b1.button(t("btn.search"), type="primary", width='stretch')
    if "rpt02_run" not in st.session_state:
        st.session_state.rpt02_run = True
    if search:
        st.session_state.rpt02_run = True
    if not st.session_state.rpt02_run:
        return

    where = ["YEAR(po.purchase_order_date)=%s"]
    params = [year]
    if vid:
        where.append("po.vendor_id=%s"); params.append(vid)
    if mtype is not None:
        where.append("p.machine_type=%s"); params.append(mtype)
    if po_status != "All":
        where.append("po.purchase_order_status=%s"); params.append(po_status)
    if isinstance(dr, (tuple, list)) and len(dr) == 2:
        where.append("DATE(po.purchase_order_date) BETWEEN %s AND %s")
        params += [dr[0].strftime("%Y-%m-%d"), dr[1].strftime("%Y-%m-%d")]

    sql = f"""
        SELECT po.purchase_order_id, po.purchase_order_date, po.purchase_order_status,
               v.vendor_name, p.product_no, p.product_name, p.manufacturer,
               p.machine_type, poi.quantity, poi.unit_price,
               (poi.quantity * poi.unit_price) AS total_price,
               (SELECT MIN(i.invoice_date) FROM invoice i
                WHERE i.purchase_order_id=po.purchase_order_id) AS receive_date
        FROM purchase_order po
        JOIN vendor v ON v.vendor_id=po.vendor_id
        JOIN purchase_order_item poi ON poi.purchase_order_id=po.purchase_order_id
        JOIN product p ON p.product_no=poi.product_no
        WHERE {' AND '.join(where)}
        ORDER BY v.vendor_name, po.purchase_order_date, po.purchase_order_id
    """
    df = db.query_df(sql, params)
    if df.empty:
        st.info(t("r2.no_data", year=year, status=(t("word.all") if po_status == "All"
                                                   else t(f"st.{po_status}"))))
        return

    def serials_for(po_id, pname):
        rows = db.query_df(
            """SELECT m.serial_number, m.machine_status, m.disposal_date, m.disposal_reason
               FROM machine m JOIN invoice i ON i.invoice_number=m.invoice_number
               WHERE i.purchase_order_id=%s AND m.machine_name=%s""", (po_id, pname))
        if rows.empty:
            return "", "", ""
        sns = ", ".join(ui.sn(int(s)) for s in rows["serial_number"])
        disp = rows[rows["machine_status"] == "Disposed"]
        ddate = ", ".join(pd.to_datetime(disp["disposal_date"]).dt.strftime("%m/%d/%Y")) if not disp.empty else ""
        dreason = ", ".join(disp["disposal_reason"].dropna().astype(str)) if not disp.empty else ""
        return sns, ddate, dreason

    extra = df.apply(lambda r: serials_for(int(r.purchase_order_id), r.product_name),
                     axis=1, result_type="expand")
    df["serials"], df["disposal_date"], df["disposal_reason"] = extra[0], extra[1], extra[2]

    def disposed_cost(po_id, pname, unit):
        row = db.query_one(
            """SELECT COUNT(*) AS n FROM machine m JOIN invoice i
               ON i.invoice_number=m.invoice_number
               WHERE i.purchase_order_id=%s AND m.machine_name=%s
               AND m.machine_status='Disposed'""", (po_id, pname))
        return float((row or {}).get("n", 0)) * float(unit)
    df["disposed_cost"] = df.apply(
        lambda r: disposed_cost(int(r.purchase_order_id), r.product_name, r.unit_price), axis=1)

    # ---------------- summary ----------------
    total_amt = float(df["total_price"].sum())
    disposed_total = float(df["disposed_cost"].sum())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("r2.m_lines"), len(df))
    m2.metric(t("r2.m_vendors"), df["vendor_name"].nunique())
    m3.metric(t("r2.m_total", year=year), ui.money(total_amt))
    m4.metric(t("r2.m_disposed"), ui.money(disposed_total))

    out = df.copy()
    out["PO Number"] = out["purchase_order_id"].map(lambda x: f"{int(x):05d}")
    out["po_status_disp"] = out["purchase_order_status"].map(lambda x: t(f"st.{x}"))
    exp = out[["PO Number", "purchase_order_date", "vendor_name", "product_no",
               "product_name", "manufacturer", "machine_type", "quantity",
               "unit_price", "total_price", "serials", "receive_date",
               "po_status_disp", "disposal_date", "disposal_reason"]]
    exp.columns = [t("r2.c_pono"), t("r2.c_podate"), t("r2.f_vendor"), t("r2.c_pno"),
                   t("c.machine"), t("c.manuf"), t("r2.f_type"), t("r2.c_qty"),
                   t("r2.c_unit"), t("r2.c_total"), t("r2.c_serials"), t("r2.c_receive"),
                   t("r2.f_status"), t("r2.c_ddate"), t("r2.c_dreason")]
    e1, e2, _ = st.columns([1, 1, 4])
    e1.download_button(t("btn.export_excel"),
                       export.to_excel_bytes(exp, f"Purchases {year}"),
                       file_name=f"annual_purchases_{year}.xlsx", width='stretch')
    if e2.button(t("btn.print"), width='stretch'):
        st.toast(t("msg.printed_short"))
    st.markdown("---")

    # ---------------- grouped by vendor ----------------
    for vendor, gv in df.groupby("vendor_name", sort=False):
        st.markdown(f"#### 🏷️ {vendor}")
        tdf = gv.copy()
        tdf["PO Number"] = tdf["purchase_order_id"].map(lambda x: f"{int(x):05d}")
        tdf["Product"] = tdf["product_name"] + " — " + tdf["manufacturer"].fillna("")
        tdf["po_status_disp"] = tdf["purchase_order_status"].map(lambda x: t(f"st.{x}"))
        show = tdf[["PO Number", "purchase_order_date", "product_no", "Product",
                    "machine_type", "quantity", "unit_price", "total_price",
                    "serials", "receive_date", "po_status_disp",
                    "disposal_date", "disposal_reason"]].rename(columns={
            "PO Number": t("r2.c_pono"), "purchase_order_date": t("r2.c_podate"),
            "product_no": t("r2.c_pno"), "Product": t("r2.c_product"),
            "machine_type": t("r2.f_type"), "quantity": t("r2.c_qty"),
            "unit_price": t("r2.c_unit"), "total_price": t("r2.c_total"),
            "serials": t("r2.c_serials"), "receive_date": t("r2.c_receive"),
            "po_status_disp": t("r2.f_status"), "disposal_date": t("r2.c_ddate"),
            "disposal_reason": t("r2.c_dreason")})
        st.dataframe(
            show, hide_index=True, width='stretch',
            column_config={
                t("r2.c_unit"): st.column_config.NumberColumn(format="$%.2f"),
                t("r2.c_total"): st.column_config.NumberColumn(format="$%.2f"),
                t("r2.c_podate"): st.column_config.DatetimeColumn(format="MM/DD/YYYY"),
                t("r2.c_receive"): st.column_config.DatetimeColumn(format="MM/DD/YYYY"),
            })
        sub = float(gv["total_price"].sum())
        st.markdown(
            f"<div style='text-align:right;font-weight:700;color:#0F2A4A'>"
            f"{t('r2.subtotal', vendor=vendor, amt=ui.money(sub), n=len(gv), q=int(gv['quantity'].sum()))}"
            f"</div>", unsafe_allow_html=True)
        st.markdown("---")

    c1, c2 = st.columns(2)
    c1.markdown(
        f"<div style='font-size:1.05rem;font-weight:800;color:#C8102E'>"
        f"{t('r2.grand', year=year, n=len(df), amt=ui.money(total_amt))}</div>",
        unsafe_allow_html=True)
    c2.markdown(
        f"<div style='text-align:right;font-size:1.05rem;font-weight:800;color:#9a6700'>"
        f"{t('r2.disposed', amt=ui.money(disposed_total))}</div>",
        unsafe_allow_html=True)
