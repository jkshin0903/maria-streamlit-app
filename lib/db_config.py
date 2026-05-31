# -*- coding: utf-8 -*-
"""Load Aiven / MariaDB connection settings from db.ini or Streamlit secrets."""
from __future__ import annotations

import configparser
import ssl
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _section_to_dict(section) -> dict:
    if hasattr(section, "to_dict"):
        return section.to_dict()
    return dict(section)


def _load_ini() -> dict:
    ini_path = _project_root() / "db. ini"
    if not ini_path.is_file():
        raise FileNotFoundError(
            f"Missing {ini_path.name}. Copy db.ini.example to db.ini and fill in credentials."
        )
    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")
    if "database" not in parser:
        raise ValueError(f"{ini_path.name} must contain a [database] section.")
    return _section_to_dict(parser["database"])


def _load_secrets() -> dict | None:
    try:
        import streamlit as st

        if "database" in st.secrets:
            return _section_to_dict(st.secrets["database"])
    except Exception:
        pass
    return None


def load_settings() -> dict:
    """Prefer Streamlit secrets when available; otherwise read db.ini."""
    return _load_secrets() or _load_ini()


def _database_name(settings: dict) -> str:
    name = settings.get("name") or settings.get("database")
    if not name:
        raise ValueError("Database name is required (use 'name' in config).")
    return name


def _ssl_context(settings: dict) -> ssl.SSLContext | None:
    ca_pem = settings.get("ca_pem", "").strip()
    ssl_ca = settings.get("ssl_ca", "").strip()

    if ca_pem:
        ctx = ssl.create_default_context(cadata=ca_pem)
    elif ssl_ca:
        ca_path = Path(ssl_ca)
        if not ca_path.is_absolute():
            ca_path = _project_root() / ca_path
        if not ca_path.is_file():
            raise FileNotFoundError(f"SSL CA file not found: {ca_path}")
        ctx = ssl.create_default_context(cafile=str(ca_path))
    else:
        return None

    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def get_connect_kwargs(*, autocommit=True, cursorclass=None) -> dict:
    settings = load_settings()
    kwargs = dict(
        host=settings["host"],
        port=int(settings["port"]),
        user=settings["user"],
        password=settings["password"],
        database=_database_name(settings),
        charset=settings.get("charset", "utf8mb4"),
        autocommit=autocommit,
    )
    if cursorclass is not None:
        kwargs["cursorclass"] = cursorclass

    for key in ("connect_timeout", "read_timeout", "write_timeout"):
        if key in settings and settings[key] not in (None, ""):
            kwargs[key] = int(settings[key])

    ssl_ctx = _ssl_context(settings)
    if ssl_ctx is not None:
        kwargs["ssl"] = ssl_ctx

    return kwargs
