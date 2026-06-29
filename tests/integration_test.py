# integration_test.py v3-fixed
# Full end‑to‑end test: TelemetryCache → DBWriter → SQL temp tables (no MQTT)

import os
import pyodbc
import pytest
from dotenv import load_dotenv

from solaris_logger.cache import TelemetryCache
from solaris_logger.db_writer import DBWriter

load_dotenv()

SQL_DRIVER   = os.getenv("SQL_DRIVER")
SQL_SERVER   = os.getenv("SQL_SERVER")
SQL_USER     = os.getenv("SQL_USER")
SQL_PASS     = os.getenv("SQL_PASS")
SQL_DATABASE = os.getenv("SQL_DATABASE")

TABLE_PREFIX = "itest_"   # temp tables you can inspect in SSMS

TEST_TABLES = {
    "live":  f"{TABLE_PREFIX}live_telemetry",
    "min15": f"{TABLE_PREFIX}summary_15min",
    "daily": f"{TABLE_PREFIX}summary_daily",
}

def build_conn_string():
    return (
        f"Driver={{{SQL_DRIVER}}};"
        f"Server={SQL_SERVER};"
        f"Database={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASS};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )

def connect_db():
    return pyodbc.connect(build_conn_string())


@pytest.fixture(scope="module")
def setup_test_tables():
    conn = connect_db()
    cur = conn.cursor()

    # Drop existing temp tables
    for tbl in TEST_TABLES.values():
        cur.execute(f"""
            IF OBJECT_ID('dbo.{tbl}', 'U') IS NOT NULL
                DROP TABLE dbo.{tbl};
        """)
        conn.commit()

    # Create fresh temp tables
    cur.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['live']} (
            id INT IDENTITY PRIMARY KEY,
            timestamp DATETIME2 NOT NULL,
            metric NVARCHAR(255) NOT NULL,
            value FLOAT NULL
        );
    """)
    conn.commit()

    cur.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['min15']} (
            id INT IDENTITY PRIMARY KEY,
            timestamp DATETIME2 NOT NULL,
            metric NVARCHAR(255) NOT NULL,
            value FLOAT NULL
        );
    """)
    conn.commit()

    cur.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['daily']} (
            id INT IDENTITY PRIMARY KEY,
            summary_date DATE NOT NULL,
            metric NVARCHAR(255) NOT NULL,
            value FLOAT NULL
        );
    """)
    conn.commit()

    conn.close()
    yield


def test_full_integration(setup_test_tables):
    # 1. Populate cache manually using REAL cache keys
    cache = TelemetryCache()
    cache.update("pv_power", 1.23)
    cache.update("grid_power", 0.45)
    cache.update("battery_power", -0.10)
    cache.update("load_power", 1.68)
    cache.update("soc", 55.2)

    # 2. Write to DB using real DBWriter
    writer = DBWriter(database=SQL_DATABASE, table_prefix=TABLE_PREFIX)
    writer.connect()
    writer.write_live(cache)
    writer.write_15min(cache)
    writer.write_daily(cache)

    # 3. Verify rows exist
    conn = connect_db()
    cur = conn.cursor()

    for table in TEST_TABLES.values():
        cur.execute(f"SELECT COUNT(*) FROM dbo.{table}")
        count = cur.fetchone()[0]
        assert count > 0, f"Expected rows in {table}, got {count}"

    conn.close()
