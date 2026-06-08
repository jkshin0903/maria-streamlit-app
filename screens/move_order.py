# -*- coding: utf-8 -*-
"""SCR-IN-02 | Machine Install / Remove (Move) Order."""
from datetime import date, datetime, time

import pandas as pd
import streamlit as st

from lib import db, ui
from lib.i18n import t

MAX_LINES = 10


def _machines():
    return db.query_df(
        """SELECT m.serial_number, m.machine_name, m.manufacturer, m.machine_type,
                  m.machine_status, m.location_id, bl.location_name, bl.location_type
           FROM machine m
           LEFT JOIN business_location bl ON bl.location_id = m.location_id
           WHERE m.machine_status <> 'Disposed'
           ORDER BY m.machine_name, m.serial_number""")


def _low_perf_history(serial, location_id):
    row = db.query_one(
        """SELECT COUNT(*) AS n FROM machine_location_hst
           WHERE serial_number=%s AND location_id=%s AND performance_note='Low'""",
        (serial, location_id))
    return (row or {}).get("n", 0) > 0


def _install_history(serial):
    return db.query_df(
        """SELECT h.start_date, h.end_date, bl.location_name, h.performance_note
           FROM machine_location_hst h
           JOIN business_location bl ON bl.location_id=h.location_id
           WHERE h.serial_number=%s ORDER BY h.start_date""", (serial,))


def render():
    ui.appbar()
    ui.screen_header("SCR-IN-02", t("mo.title"), t("mo.sub"))

    user = ui.current_user()
    techs = db.get_technicians()
    sites = db.get_sites()
    locs = db.get_locations()
    machines = _machines()

    if machines.empty:
        st.error(t("mo.no_machine"))
        return

    loc_name = {int(r.location_id): r.location_name for r in locs.itertuples()}
    site_opts = {int(r.location_id): f"{r.location_name} ({r.city})" for r in sites.itertuples()}
    warehouse_id = int(locs[locs.location_type == "Warehouse"].iloc[0].location_id)

    if "mo_lines" not in st.session_state:
        st.session_state.mo_lines = []

    # ---------------- header ----------------
    ui.section(t("mo.sec_header"))
    next_order = db.next_id("order", "order_id")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.text_input(t("mo.order_no"), value=f"{next_order:05d}", disabled=True)
    with c2:
        st.date_input(t("mo.order_date"), value=date.today(), format="MM/DD/YYYY", disabled=True)
    with c3:
        regions = [t("word.all_regions")] + sorted(techs["region"].dropna().unique().tolist())
        region = st.selectbox(t("mo.region"), regions)
    with c4:
        st.text_input(t("mo.issuing"), value=user, disabled=True)

    tf = techs if region == t("word.all_regions") else techs[techs.region == region]
    tech_opts = {int(r.technician_id): f"{r.technician_name} · {r.region}"
                 for r in tf.itertuples()}
    if not tech_opts:
        tech_opts = {int(r.technician_id): r.technician_name for r in techs.itertuples()}
    tech_id = st.selectbox(t("mo.tech"), options=list(tech_opts.keys()),
                           format_func=lambda x: tech_opts[x], index=0)

    sc1, sc2 = st.columns(2)
    with sc1:
        sched_date = st.date_input(t("mo.sched_date"), value=date.today(),
                                   min_value=date.today(), format="MM/DD/YYYY",
                                   help=t("mo.sched_date_help"))
    with sc2:
        sched_time = st.time_input(t("mo.sched_time"), value=time(13, 0), step=900)

    # ---------------- machine line builder ----------------
    ui.section(t("mo.sec_add"))
    mlabels = {int(r.serial_number):
               f"{ui.sn(int(r.serial_number))} · {r.machine_name} ({r.machine_type})"
               for r in machines.itertuples()}
    bc1, bc2 = st.columns([2, 1])
    with bc1:
        serial = st.selectbox(t("mo.sn"), options=list(mlabels.keys()),
                              format_func=lambda x: mlabels[x], index=None,
                              placeholder=t("mo.sn_ph"))
    mrow = machines[machines.serial_number == serial].iloc[0] if serial is not None else None
    act_labels = {"Install": t("mo.act_install"), "Remove": t("mo.act_remove"),
                  "Move": t("mo.act_move")}
    with bc2:
        order_type = st.radio(t("mo.action"), ["Install", "Remove", "Move"],
                              format_func=lambda k: act_labels[k])

    if mrow is not None:
        cur_loc_id = int(mrow.location_id) if pd.notna(mrow.location_id) else None
        i1, i2, i3 = st.columns(3)
        i1.metric(t("mo.cur_loc"), loc_name.get(cur_loc_id, "—"))
        i2.markdown(f"**{t('mo.status')}**<br>" + ui.status_pill(mrow.machine_status),
                    unsafe_allow_html=True)
        i3.metric(t("mo.type_mfr"), f"{mrow.machine_type} · {mrow.manufacturer}")
        hist = _install_history(int(serial))
        if not hist.empty:
            with st.expander(t("mo.hist_exp")):
                h = hist.copy()
                h["Period"] = h.apply(
                    lambda r: f"{pd.to_datetime(r.start_date):%m/%d/%Y} → " +
                    (f"{pd.to_datetime(r.end_date):%m/%d/%Y}" if pd.notna(r.end_date) else "present"),
                    axis=1)
                st.dataframe(h[["location_name", "Period", "performance_note"]]
                             .rename(columns={"location_name": t("mo.h_loc"),
                                              "Period": t("mo.h_period"),
                                              "performance_note": t("mo.h_perf")}),
                             hide_index=True, width='stretch')
    else:
        cur_loc_id = None

    lc1, lc2 = st.columns(2)
    with lc1:
        need_install = order_type in ("Install", "Move")
        install_loc = st.selectbox(
            t("mo.install_loc"), options=list(site_opts.keys()),
            format_func=lambda x: site_opts[x], index=None,
            placeholder=t("mo.install_ph"), disabled=not need_install,
            help=t("mo.install_loc_help"))
    with lc2:
        need_remove = order_type in ("Remove", "Move")
        default_remove = cur_loc_id if (cur_loc_id in site_opts) else None
        remove_loc = st.selectbox(
            t("mo.remove_loc"), options=list(site_opts.keys()),
            format_func=lambda x: site_opts[x],
            index=(list(site_opts.keys()).index(default_remove)
                   if default_remove in site_opts else None),
            placeholder=t("mo.remove_ph"), disabled=not need_remove,
            help=t("mo.remove_loc_help"))

    if mrow is not None:
        il = install_loc if need_install else None
        rl = remove_loc if need_remove else None
        if il and rl and il == rl:
            st.warning(t("mo.warn_same"))
        if il and cur_loc_id == il and str(mrow.machine_status) == "Active":
            st.warning(t("mo.warn_already", sn=ui.sn(int(serial)), loc=loc_name.get(il)))
        if il and _low_perf_history(int(serial), il):
            st.warning(t("mo.warn_lowperf", loc=loc_name.get(il)))

    if st.button(t("mo.add_btn"), width='content'):
        err = None
        il = install_loc if need_install else None
        rl = remove_loc if need_remove else None
        if serial is None:
            err = t("mo.err_sn")
        elif not il and not rl:
            err = t("mo.err_loc")
        elif il and rl and il == rl:
            err = t("mo.warn_same")
        elif any(l["serial"] == serial for l in st.session_state.mo_lines):
            err = t("mo.err_dupsn", sn=ui.sn(int(serial)))
        elif len(st.session_state.mo_lines) >= MAX_LINES:
            err = t("mo.err_maxlines", n=MAX_LINES)
        if err:
            st.error(err)
        else:
            st.session_state.mo_lines.append(dict(
                serial=int(serial), name=mrow.machine_name, type=mrow.machine_type,
                order_type=order_type,
                install_loc=il, remove_loc=rl, current=cur_loc_id))
            st.rerun()

    # ---------------- current order lines ----------------
    if st.session_state.mo_lines:
        ui.section(t("mo.lines_sec", n=len(st.session_state.mo_lines), m=MAX_LINES))
        tbl = pd.DataFrame([{
            t("mo.c_sn"): ui.sn(l["serial"]), t("mo.c_machine"): l["name"],
            t("mo.c_type"): l["type"], t("mo.c_act"): act_labels.get(l["order_type"], l["order_type"]),
            t("mo.c_from"): loc_name.get(l["remove_loc"], "—"),
            t("mo.c_to"): loc_name.get(l["install_loc"], "—"),
        } for l in st.session_state.mo_lines])
        st.dataframe(tbl, hide_index=True, width='stretch')
        rem = st.selectbox(t("mo.rm_line"),
                           options=[None] + list(range(len(st.session_state.mo_lines))),
                           format_func=lambda x: "—" if x is None else
                           f"Line {x+1}: {ui.sn(st.session_state.mo_lines[x]['serial'])}")
        if rem is not None and st.button(t("mo.rm_line_btn")):
            st.session_state.mo_lines.pop(rem)
            st.rerun()

    notes = st.text_area(t("mo.notes"), placeholder=t("mo.notes_ph"))

    st.markdown("---")
    a1, a2, _ = st.columns([1, 1, 4])
    save_draft = a1.button(t("mo.save_draft"), width='stretch')
    submit = a2.button(t("mo.submit"), type="primary", width='stretch')

    def _persist(status):
        if not st.session_state.mo_lines:
            st.error(t("mo.need_line"))
            return False
        oid = db.next_id("order", "order_id")
        sched_dt = datetime.combine(sched_date, sched_time)
        rows = []
        for l in st.session_state.mo_lines:
            if l["order_type"] == "Install":
                frm = warehouse_id; to = l["install_loc"]
            elif l["order_type"] == "Remove":
                frm = l["remove_loc"] or l["current"]; to = warehouse_id
            else:  # Move
                frm = l["remove_loc"] or l["current"]; to = l["install_loc"]
            rows.append((oid, l["serial"], int(tech_id), frm, to, to,
                         l["order_type"], status, None,
                         date.today().strftime("%Y-%m-%d %H:%M:%S"),
                         sched_dt.strftime("%Y-%m-%d %H:%M:%S"), None, notes or None, user))
            oid += 1
        db.execute_many(
            "INSERT INTO `order` (order_id,serial_number,technician_id,from_location_id,"
            "to_location_id,location_id,order_type,order_status,competion_date,request_date,"
            "scheduled_datetime,signature,notes,issuing_manager) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
        return True

    if save_draft and _persist("Draft"):
        st.success(t("mo.draft_ok", n=len(st.session_state.mo_lines)))
        st.session_state.mo_lines = []
    if submit and _persist("Submitted"):
        st.success(t("mo.submit_ok", order=f"{next_order:05d}", tech=tech_opts[tech_id]))
        st.balloons()
        st.session_state.mo_lines = []

    # ---------------- field completion (BR-06) ----------------
    st.markdown("---")
    ui.section(t("mo.sec_complete"))
    open_orders = db.query_df(
        """SELECT o.order_id, o.serial_number, o.order_type, o.order_status,
                  o.from_location_id, o.to_location_id, m.machine_name
           FROM `order` o JOIN machine m ON m.serial_number=o.serial_number
           WHERE o.order_status IN ('Submitted','Draft')
           ORDER BY o.order_id DESC""")
    if open_orders.empty:
        st.caption(t("mo.no_open"))
    else:
        opt = {int(r.order_id):
               f"#{int(r.order_id):05d} · {act_labels.get(r.order_type, r.order_type)} · "
               f"{ui.sn(int(r.serial_number))} {r.machine_name}"
               for r in open_orders.itertuples()}
        sel = st.selectbox(t("mo.open_order"), options=list(opt.keys()),
                           format_func=lambda x: opt[x])
        sig = st.text_input(t("mo.signature"), placeholder=t("mo.signature_ph"))
        cc1, cc2 = st.columns(2)
        comp_date = cc1.date_input(t("mo.comp_date"), value=date.today(), format="MM/DD/YYYY")
        comp_time = cc2.time_input(t("mo.comp_time"), value=time(15, 0), step=900)
        done = st.checkbox(t("mo.comp_check"))
        if st.button(t("mo.comp_btn"), type="primary"):
            if not done:
                st.warning(t("mo.comp_need_check"))
            elif not sig.strip():
                st.warning(t("mo.comp_need_sig"))
            else:
                o = open_orders[open_orders.order_id == sel].iloc[0]
                comp_dt = datetime.combine(comp_date, comp_time)
                new_loc = int(o.to_location_id)
                db.execute("UPDATE machine_location_hst SET end_date=%s "
                           "WHERE serial_number=%s AND end_date IS NULL",
                           (comp_dt.strftime("%Y-%m-%d %H:%M:%S"), int(o.serial_number)))
                hid = db.next_id("machine_location_hst", "hst_id")
                db.execute(
                    "INSERT INTO machine_location_hst (hst_id,serial_number,location_id,"
                    "start_date,end_date,performance_note) VALUES (%s,%s,%s,%s,NULL,NULL)",
                    (hid, int(o.serial_number), new_loc,
                     comp_dt.strftime("%Y-%m-%d %H:%M:%S")))
                new_status = "In Warehouse" if str(o.order_type) == "Remove" else "Active"
                db.execute(
                    "UPDATE machine SET location_id=%s, machine_status=%s, "
                    "installation_date=%s WHERE serial_number=%s",
                    (new_loc, new_status, comp_dt.strftime("%Y-%m-%d %H:%M:%S"),
                     int(o.serial_number)))
                db.execute(
                    "UPDATE `order` SET order_status='Completed', competion_date=%s, "
                    "signature=%s WHERE order_id=%s",
                    (comp_dt.strftime("%Y-%m-%d %H:%M:%S"), sig.strip(), int(sel)))
                db.clear_lookup_cache()
                st.success(t("mo.comp_ok", order=f"{sel:05d}", sn=ui.sn(int(o.serial_number)),
                             status=t(f"st.{new_status}"), loc=loc_name.get(new_loc)))
                st.rerun()
