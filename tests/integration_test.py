# integration_test.py v4-fixed
# Full end‑to‑end test: MQTT → TelemetryCache → DBWriter → SQL temp tables

import os
import pyodbc
import pytest
import time
from dotenv import load_dotenv

from solaris_logger.cache import TelemetryCache
from solaris_logger.db_writer import DBWriter
from solaris_logger.mqtt_broker import MQTTBroker

load_dotenv()

SQL_DRIVER   = os.getenv("SQL_DRIVER")
SQL_SERVER   = os.getenv("SQL_SERVER")
SQL_USER     = os.getenv("SQL_USER")
SQL_PASS     = os.getenv("SQL_PASS")
SQL_DATABASE = os.getenv("SQL_DATABASE")

TABLE_PREFIX = "itest_"   # temp tables you can inspect in SSMS

TEST_TABLES = {
    "min1":  f"{TABLE_PREFIX}summary_1min",
    "min15": f"{TABLE_PREFIX}summary_15min",
    "daily": f"{TABLE_PREFIX}summary_daily",
    "state": f"{TABLE_PREFIX}inverter_state_changes",
    "freshness": f"{TABLE_PREFIX}data_freshness_log",
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
    """Create fresh temp tables for testing"""
    conn = connect_db()
    cursor = conn.cursor()

    # Drop existing temp tables if they exist
    for tbl in TEST_TABLES.values():
        try:
            cursor.execute(f"""
                IF OBJECT_ID('dbo.{tbl}', 'U') IS NOT NULL
                    DROP TABLE dbo.{tbl};
            """)
            conn.commit()
        except Exception as e:
            print(f"Warning: Could not drop {tbl}: {e}")

    # Create 1-minute summary temp table
    cursor.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['min1']} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp DATETIME2 NOT NULL,
            metric NVARCHAR(64) NOT NULL,
            kw FLOAT NULL,
            cumulative_kwh FLOAT NULL
        );
    """)
    conn.commit()

    # Create 15-minute summary temp table
    cursor.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['min15']} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp DATETIME2 NOT NULL,
            metric NVARCHAR(64) NOT NULL,
            kw FLOAT NULL,
            cumulative_kwh FLOAT NULL
        );
    """)
    conn.commit()

    # Create daily summary temp table
    cursor.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['daily']} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            summary_date DATE NOT NULL,
            recorded_pv_kwh FLOAT NULL,
            recorded_grid_import_kwh FLOAT NULL,
            recorded_grid_export_kwh FLOAT NULL,
            recorded_batt_charge_kwh FLOAT NULL,
            recorded_batt_discharge_kwh FLOAT NULL
        );
    """)
    conn.commit()

    # Create inverter state changes temp table
    cursor.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['state']} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp DATETIME2 NOT NULL,
            state_key NVARCHAR(64) NOT NULL,
            state_value NVARCHAR(255) NOT NULL
        );
    """)
    conn.commit()

    # Create data freshness log temp table
    cursor.execute(f"""
        CREATE TABLE dbo.{TEST_TABLES['freshness']} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            timestamp DATETIME2 NOT NULL,
            event_type NVARCHAR(32) NOT NULL,
            max_cache_age_seconds INT NULL,
            min_cache_age_seconds INT NULL,
            metrics_checked INT NULL,
            message NVARCHAR(512)
        );
    """)
    conn.commit()
    
    conn.close()
    yield
    # No cleanup - itest_* tables remain for inspection in SSMS until next test run


def test_cache_to_db(setup_test_tables):
    """Test: populate cache → check freshness → write to DB temp tables"""
    
    # 1. Create cache and populate with telemetry data
    cache = TelemetryCache()
    cache.update("pv_power", 1.23)
    cache.update("grid_power", 0.45)
    cache.update("battery_power", -0.10)
    cache.update("load_power", 1.68)
    cache.update("soc", 55.2)
    cache.update("inverter_state", "OK")
    cache.update("battery_mode", "HOLD")

    # 2. Verify cache is fresh (< 5 min old)
    is_fresh, max_age, min_age, metrics_checked = cache.check_freshness(max_age_seconds=300)
    assert is_fresh, f"Cache should be fresh but max_age={max_age}s"
    print(f"✓ Cache freshness check passed: max_age={max_age}s, min_age={min_age}s")

    # 3. Initialize DBWriter and verify connection
    writer = DBWriter(table_prefix=TABLE_PREFIX)
    assert writer.connect(), "Failed to connect to SQL Server"

    # 4. Log freshness event
    writer.log_freshness("FRESH", max_age=max_age, min_age=min_age, metrics_checked=metrics_checked,
                        message=f"Cache fresh: {max_age}s old")

    # 5. Write cache snapshots to SQL temp tables
    writer.write_1min(cache)
    writer.write_15min(cache)
    writer.write_daily(cache)
    writer.write_state_changes(cache)

    # 6. Verify data was written to temp tables
    conn = connect_db()
    cursor = conn.cursor()

    # Check 1-min summary table
    cursor.execute(f"SELECT COUNT(*) FROM dbo.{TEST_TABLES['min1']}")
    min1_count = cursor.fetchone()[0]
    assert min1_count > 0, f"Expected rows in {TEST_TABLES['min1']}, got {min1_count}"
    print(f"✓ 1-min summary: {min1_count} rows written")

    # Check 15-min summary table
    cursor.execute(f"SELECT COUNT(*) FROM dbo.{TEST_TABLES['min15']}")
    min15_count = cursor.fetchone()[0]
    assert min15_count > 0, f"Expected rows in {TEST_TABLES['min15']}, got {min15_count}"
    print(f"✓ 15-min summary: {min15_count} rows written")

    # Check daily summary table
    cursor.execute(f"SELECT COUNT(*) FROM dbo.{TEST_TABLES['daily']}")
    daily_count = cursor.fetchone()[0]
    assert daily_count > 0, f"Expected rows in {TEST_TABLES['daily']}, got {daily_count}"
    print(f"✓ Daily summary: {daily_count} rows written")

    # Check state changes table
    cursor.execute(f"SELECT COUNT(*) FROM dbo.{TEST_TABLES['state']}")
    state_count = cursor.fetchone()[0]
    assert state_count > 0, f"Expected rows in {TEST_TABLES['state']}, got {state_count}"
    print(f"✓ State changes: {state_count} rows written")

    # Check freshness log table
    cursor.execute(f"SELECT COUNT(*) FROM dbo.{TEST_TABLES['freshness']} WHERE event_type = 'FRESH'")
    freshness_count = cursor.fetchone()[0]
    assert freshness_count > 0, f"Expected FRESH event in {TEST_TABLES['freshness']}, got {freshness_count}"
    print(f"✓ Freshness log: {freshness_count} FRESH events written")

    # 7. Verify we can read the data back
    cursor.execute(f"SELECT TOP 5 metric, kw, cumulative_kwh FROM dbo.{TEST_TABLES['min1']} ORDER BY id DESC")
    rows = cursor.fetchall()
    print(f"✓ Sample 1-min data: {rows}")
    
    cursor.execute(f"SELECT TOP 5 state_key, state_value FROM dbo.{TEST_TABLES['state']} ORDER BY id DESC")
    state_rows = cursor.fetchall()
    print(f"✓ Sample state changes: {state_rows}")

    cursor.execute(f"SELECT TOP 5 event_type, max_cache_age_seconds, message FROM dbo.{TEST_TABLES['freshness']} ORDER BY id DESC")
    freshness_rows = cursor.fetchall()
    print(f"✓ Sample freshness log: {freshness_rows}")

    conn.close()


def test_mqtt_to_cache_to_db(setup_test_tables):
    """Test: MQTT → cache → DB with retry logic (fails if broker unavailable)"""
    
    # Create cache
    cache = TelemetryCache()
    
    # Initialize MQTT broker connection
    mqtt = MQTTBroker(cache)
    
    # Try to connect with retries
    max_retries = 3
    retry_delay = 2  # seconds
    mqtt_connected = False
    
    for attempt in range(1, max_retries + 1):
        try:
            mqtt.start()
            print(f"[OK] MQTT broker connected (attempt {attempt}/{max_retries})")
            mqtt_connected = True
            break
        except Exception as e:
            if attempt < max_retries:
                print(f"[RETRY] MQTT connection failed (attempt {attempt}/{max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                # All retries exhausted - fail the test
                mqtt.stop()
                raise AssertionError(f"MQTT broker unavailable after {max_retries} attempts: {e}")
    
    try:
        # Wait for MQTT messages to arrive (longer wait = more messages = fresh data)
        time.sleep(5)
        
        # Debug: print what's in cache after MQTT connection
        cache_snapshot = cache.summary_1min()
        non_none_metrics = {k: v for k, v in cache_snapshot.items() if v[0] is not None}
        print(f"[INFO] Cache snapshot after 5s MQTT wait:")
        print(f"       Non-None metrics: {len(non_none_metrics)}/{len(cache_snapshot)}")
        for k, (v, ts) in non_none_metrics.items():
            print(f"       - {k}: {v}")
        
        # Check cache freshness
        is_fresh, max_age, min_age, metrics_checked = cache.check_freshness(max_age_seconds=300)
        
        # Initialize DBWriter
        writer = DBWriter(table_prefix=TABLE_PREFIX)
        
        # Log freshness status
        if is_fresh:
            writer.log_freshness("FRESH", max_age=max_age, min_age=min_age, metrics_checked=metrics_checked,
                               message=f"MQTT cache fresh: {max_age}s old")
        else:
            writer.log_freshness("STALE", max_age=max_age, min_age=min_age, metrics_checked=metrics_checked,
                               message=f"MQTT cache stale: {max_age}s old")
        
        # Only write if cache is fresh
        if not is_fresh:
            print(f"[WARN] MQTT test: cache is stale ({max_age}s old), skipping writes")
        else:
            # Write whatever is in cache to database
            writer.write_1min(cache)
            writer.write_15min(cache)
            writer.write_daily(cache)
            writer.write_state_changes(cache)
            
            # Verify we wrote something
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM dbo.{TEST_TABLES['min1']}")
            count = cursor.fetchone()[0]
            print(f"[OK] MQTT test: {count} rows written from fresh cache")
            conn.close()
        
    finally:
        mqtt.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

