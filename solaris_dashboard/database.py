"""Database connection and query utilities for Solaris Dashboard."""

import os
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def get_connection_string():
    """Build SQLAlchemy connection string from environment variables."""
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("SQL_SERVER")
    user = os.getenv("SQL_USER")
    password = os.getenv("SQL_PASS")
    database = os.getenv("SQL_DATABASE")
    trust_cert = os.getenv("SQL_TRUST_CERT", "yes").lower()

    # Build ODBC connection string
    odbc_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"UID={user};"
        f"PWD={password};"
        f"DATABASE={database};"
        f"Encrypt=no;"
        f"TrustServerCertificate={trust_cert};"
    )

    # SQLAlchemy connection string
    return f"mssql+pyodbc:///?odbc_connect={odbc_string}"


def get_engine():
    """Get SQLAlchemy engine."""
    return create_engine(get_connection_string(), fast_executemany=True)


def query_summary_1min(hours=24):
    """Get last N hours of 1-minute summary data."""
    engine = get_engine()
    cutoff = datetime.now() - timedelta(hours=hours)

    query = f"""
    SELECT timestamp, metric, kw, cumulative_kwh
    FROM dbo.summary_1min
    WHERE timestamp >= '{cutoff.isoformat()}'
    ORDER BY timestamp DESC
    """

    return pd.read_sql(query, engine)


def query_summary_15min(days=7):
    """Get last N days of 15-minute summary data."""
    engine = get_engine()
    cutoff = datetime.now() - timedelta(days=days)

    query = f"""
    SELECT timestamp, metric, kw, cumulative_kwh
    FROM dbo.summary_15min
    WHERE timestamp >= '{cutoff.isoformat()}'
    ORDER BY timestamp DESC
    """

    return pd.read_sql(query, engine)


def query_summary_daily(days=365):
    """Get last N days of daily summary data."""
    engine = get_engine()
    cutoff = datetime.now() - timedelta(days=days)

    query = f"""
    SELECT timestamp, metric, kw, cumulative_kwh
    FROM dbo.summary_daily
    WHERE timestamp >= '{cutoff.isoformat()}'
    ORDER BY timestamp DESC
    """

    return pd.read_sql(query, engine)


def query_state_changes(limit=100):
    """Get recent inverter state changes."""
    engine = get_engine()

    query = f"""
    SELECT TOP {limit} timestamp, state_key, state_value
    FROM dbo.inverter_state_changes
    ORDER BY timestamp DESC
    """

    return pd.read_sql(query, engine)


def query_freshness_log(hours=24):
    """Get recent freshness check events."""
    engine = get_engine()
    cutoff = datetime.now() - timedelta(hours=hours)

    query = f"""
    SELECT timestamp, event_type, max_cache_age_seconds, message
    FROM dbo.data_freshness_log
    WHERE timestamp >= '{cutoff.isoformat()}'
    ORDER BY timestamp DESC
    """

    return pd.read_sql(query, engine)


def get_latest_metrics():
    """Get most recent metric values."""
    engine = get_engine()

    query = """
    WITH latest AS (
        SELECT timestamp, metric, kw, cumulative_kwh,
               ROW_NUMBER() OVER (PARTITION BY metric ORDER BY timestamp DESC) as rn
        FROM dbo.summary_1min
    )
    SELECT timestamp, metric, kw, cumulative_kwh
    FROM latest
    WHERE rn = 1
    """

    return pd.read_sql(query, engine)
