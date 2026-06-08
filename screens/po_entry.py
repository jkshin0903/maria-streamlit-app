# -*- coding: utf-8 -*-
"""SCR-IN-01 | Purchase Order Entry."""
from datetime import date

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import t

MAX_LINES = 20


def _blank_lines():
    return pd.DataFrame([
        {"product": None, "manufacturer": "", "machine_type": "",
         "quantity": 1, "unit_price": 0.0}
    ])


def render():
    ui.appbar()
    ui.screen_header("SCR-IN-01", t("po.title"), t("po.sub"))

    user = ui.current_user()
    products = db.get_products()
    vendors = db.get_vendors()

    if products.empty or vendors.empty:
        st.error(t("po.no_master"))
        return

    prod_label = {int(r.product_no): f"{int(r.product_no)} — {r.product_name}"
                  for r in products.itertuples()}
    prod_info = {int(r.product_no): dict(name=r.product_name,
                 manufacturer=r.manufacturer or "", machine_type=r.machine_type or "",
                 list_price=float(r.list_price or 0)) for r in products.itertuples()}

    if "po_lines" not in st.session_state:
        st.session_state.po_lines = _blank_lines()

    # ---------------- header section ----------------
    ui.section(t("po.sec_header"))
    c1, c2, c3 = st.columns(3)
    next_po = db.next_id("purchase_order", "purchase_order_id")
    with c1:
        st.text_input(t("po.po_number"), value=f"{next_po:05d}", disabled=True,
                      help=t("po.po_number_help"))
    with c2:
        po_date = st.date_input(t("po.po_date"), value=date.today(),
                                max_value=date.today(), format="MM/DD/YYYY",
                                help=t("po.po_date_help"))
    with c3:
        st.text_input(t("po.buyer"), value=user, disabled=True)

    ui.section(t("po.sec_vendor"))
    vlabels = {int(r.vendor_id): r.vendor_name for r in vendors.itertuples()}
    vid = st.selectbox(t("po.vendor_name"), options=list(vlabels.keys()),
                       format_func=lambda x: vlabels[x],
                       index=None, placeholder=t("po.vendor_ph"))
    vc1, vc2, vc3 = st.columns([2, 1, 1])
    vrow = vendors[vendors.vendor_id == vid].iloc[0] if vid is not None else None
    with vc1:
        st.text_input(t("po.vendor_addr"),
                      value=(vrow.address if vrow is not None else ""), disabled=True)
    with vc2:
        st.text_input(t("po.vendor_phone"),
                      value=(vrow.phone if vrow is not None else ""), disabled=True)
    with vc3:
        vfax = vrow.fax if vrow is not None else ""
        st.text_input(t("po.vendor_fax"), value=(vfax or ""), disabled=True)

    # ---------------- line items ----------------
    ui.section(t("po.sec_lines"))
    st.caption(t("po.lines_help"))

    base_len = len(st.session_state.po_lines)
    editor_key = f"po_editor_{st.session_state.get('po_editor_nonce', 0)}"
    edited = st.data_editor(
        st.session_state.po_lines,
        num_rows="dynamic",
        width='stretch',
        key=editor_key,
        column_config={
            "product": st.column_config.SelectboxColumn(
                t("po.col_product"), options=list(prod_label.keys()),
                format_func=lambda x: prod_label.get(x, ""), required=False, width="large"),
            "manufacturer": st.column_config.TextColumn(t("po.col_manuf"), disabled=True),
            "machine_type": st.column_config.TextColumn(t("po.col_type"), disabled=True, width="small"),
            "quantity": st.column_config.NumberColumn(
                t("po.col_qty"), min_value=1, step=1, format="%d", width="small"),
            "unit_price": st.column_config.NumberColumn(
                t("po.col_unit"), min_value=0.0, step=50.0, format="$%.2f"),
        },
    )

    edited = edited.reset_index(drop=True)
    raw = edited.copy()
    for i, row in edited.iterrows():
        p = row["product"]
        if p in prod_info:
            edited.at[i, "manufacturer"] = prod_info[p]["manufacturer"]
            edited.at[i, "machine_type"] = prod_info[p]["machine_type"]
            if not row["unit_price"] or float(row["unit_price"]) == 0.0:
                edited.at[i, "unit_price"] = prod_info[p]["list_price"]
        if pd.isna(row["quantity"]) or row["quantity"] < 1:
            edited.at[i, "quantity"] = 1
    st.session_state.po_lines = edited

    # On row add/delete or auto-fill, re-init the editor under a fresh key so its
    # stale edit deltas don't reapply to the already-updated base.
    structural = len(raw) != base_len
    if structural or not edited.equals(raw):
        st.session_state.po_editor_nonce = st.session_state.get("po_editor_nonce", 0) + 1
        st.rerun()

    valid = edited[edited["product"].notna()].copy()
    valid["line_total"] = valid["quantity"].fillna(0) * valid["unit_price"].fillna(0)
    dup_products = valid["product"][valid["product"].duplicated()].unique()
    if len(dup_products):
        dup_names = ", ".join(prod_label.get(d, str(d)) for d in dup_products)
        st.warning(t("po.err_dup", names=dup_names))
    if not valid.empty:
        disp = valid.assign(
            Product=[prod_label.get(p, "") for p in valid["product"]],
            Total=valid["line_total"],
        )[["Product", "manufacturer", "machine_type", "quantity", "unit_price", "Total"]]
        disp.columns = [t("po.col_product_name"), t("po.col_manuf"), t("po.col_type"),
                        t("po.col_qty"), t("po.col_unit"), t("po.col_total")]
        st.dataframe(
            disp, hide_index=True, width='stretch',
            column_config={
                t("po.col_unit"): st.column_config.NumberColumn(format="$%.2f"),
                t("po.col_total"): st.column_config.NumberColumn(format="$%.2f"),
            })

    total_amount = float(valid["line_total"].sum()) if not valid.empty else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric(t("po.m_lines"), f"{len(valid)} / {MAX_LINES}")
    m2.metric(t("po.m_qty"), int(valid["quantity"].sum()) if not valid.empty else 0)
    m3.metric(t("po.m_total"), ui.money(total_amount))

    st.markdown("---")

    b1, b2, b3, b4 = st.columns([1, 1, 1, 3])
    save = b1.button(t("po.save"), type="primary", width='stretch')
    fax = b2.button(t("po.fax"), width='stretch')
    clear = b3.button(t("po.clear"), width='stretch')

    if clear:
        st.session_state.po_lines = _blank_lines()
        st.session_state.po_editor_nonce = st.session_state.get("po_editor_nonce", 0) + 1
        st.rerun()

    def validate():
        errs = []
        if vid is None:
            errs.append(t("po.err_vendor"))
        if len(valid) == 0:
            errs.append(t("po.err_line"))
        if len(valid) > MAX_LINES:
            errs.append(t("po.err_max", n=MAX_LINES))
        if (valid["quantity"] < 1).any():
            errs.append(t("po.err_qty"))
        if (valid["unit_price"] <= 0).any():
            errs.append(t("po.err_unit"))
        dups = valid["product"][valid["product"].duplicated()].unique()
        if len(dups):
            names = ", ".join(prod_label.get(d, str(d)) for d in dups)
            errs.append(t("po.err_dup", names=names))
        return errs

    if fax:
        if vid is None:
            st.warning(t("po.fax_no_vendor"))
        elif len(valid) == 0:
            st.warning(t("po.fax_no_line"))
        elif not (vrow.fax or "").strip():
            st.warning(t("po.fax_no_fax"))
        else:
            st.success(t("po.fax_ok", vendor=vlabels[vid], fax=vrow.fax))

    if save:
        errs = validate()
        if errs:
            for e in errs:
                st.error(e)
            return
        try:
            db.execute(
                "INSERT INTO purchase_order (purchase_order_id,vendor_id,"
                "purchase_order_date,purchase_order_status) VALUES (%s,%s,%s,%s)",
                (next_po, int(vid), po_date.strftime("%Y-%m-%d %H:%M:%S"), "Pending"))
            db.execute_many(
                "INSERT INTO purchase_order_item (product_no,purchase_order_id,"
                "quantity,unit_price) VALUES (%s,%s,%s,%s)",
                [(int(r["product"]), next_po, int(r["quantity"]), float(r["unit_price"]))
                 for _, r in valid.iterrows()])
            st.success(t("po.save_ok", po=f"{next_po:05d}", n=len(valid),
                         total=ui.money(total_amount)))
            st.balloons()
            st.session_state.po_lines = _blank_lines()
            st.session_state.po_editor_nonce = st.session_state.get("po_editor_nonce", 0) + 1
        except Exception as e:
            st.error(t("po.save_fail", e=e))
