# -*- coding: utf-8 -*-
"""Database access layer for the R&S Asset Management app."""
import pandas as pd
import pymysql
import streamlit as st

from lib.db_config import get_connect_kwargs


def _connect():
    return pymysql.connect(**get_connect_kwargs(
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    ))


def get_conn():
    """Return a live connection, reconnecting if the pooled one dropped."""
    conn = st.session_state.get("_db_conn")
    if conn is None:
        conn = _connect()
        st.session_state["_db_conn"] = conn
    else:
        try:
            conn.ping(reconnect=True)
        except Exception:
            conn = _connect()
            st.session_state["_db_conn"] = conn
    return conn


def _drop_conn():
    """Discard the cached connection so the next call rebuilds it.

    A pymysql connection is not safe to reuse after a query is interrupted
    mid-flight (e.g. Streamlit stops a rerunning script): leftover bytes stay
    on the socket and poison the next query with packet-sequence/struct errors.
    """
    conn = st.session_state.pop("_db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def _read(op, retries=1):
    """Run a read op(cursor) with one reconnect retry.

    A Streamlit rerun can interrupt a query mid-flight and leave stray bytes on
    the pooled socket, so the next read fails with a packet-sequence
    InternalError even though ping() looked healthy. Dropping the poisoned
    connection and retrying on a fresh one makes these transient errors
    transparent. Reads only — re-running them is side-effect free.
    """
    last = None
    for _ in range(retries + 1):
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                return op(cur)
        except Exception as e:
            last = e
            _drop_conn()
    raise last


def query_df(sql, params=None):
    def op(cur):
        cur.execute(sql, params or ())
        return pd.DataFrame(cur.fetchall())
    return _read(op)


def query_one(sql, params=None):
    def op(cur):
        cur.execute(sql, params or ())
        return cur.fetchone()
    return _read(op)


def execute(sql, params=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid
    except Exception:
        _drop_conn()
        raise


def execute_many(sql, seq):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, seq)
    except Exception:
        _drop_conn()
        raise


def next_id(table, pk):
    row = query_one(f"SELECT COALESCE(MAX(`{pk}`),0)+1 AS n FROM `{table}`")
    return int(row["n"])


# ----- common lookups (cached for the session) -----
@st.cache_data(ttl=30)
def get_vendors():
    return query_df("SELECT * FROM vendor ORDER BY vendor_name")


@st.cache_data(ttl=30)
def get_products():
    return query_df(
        "SELECT product_no, product_name, manufacturer, machine_type, list_price "
        "FROM product ORDER BY machine_type, product_name")


@st.cache_data(ttl=30)
def get_locations(include_internal=True):
    sql = "SELECT * FROM business_location"
    if not include_internal:
        sql += " WHERE location_type='Site'"
    sql += " ORDER BY location_type, location_name"
    return query_df(sql)


@st.cache_data(ttl=30)
def get_sites():
    return query_df(
        "SELECT * FROM business_location WHERE location_type='Site' "
        "ORDER BY city, location_name")


@st.cache_data(ttl=30)
def get_technicians():
    return query_df("SELECT * FROM technician ORDER BY technician_name")


@st.cache_data(ttl=30)
def get_machine_types():
    df = query_df("SELECT DISTINCT machine_type FROM product "
                  "WHERE machine_type IS NOT NULL ORDER BY machine_type")
    return df["machine_type"].tolist() if not df.empty else []


def clear_lookup_cache():
    st.cache_data.clear()
