# db_writer.py — Solaris v16
# Writes 1‑min, 15‑min and daily summary rows to production schema.
# Aligns with create_solar_db_schema.sql structure.

import pyodbc
import os
import logging
from datetime import datetime, UTC
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DBWriter:
    def __init__(self, table_prefix=""):
        """Initialize DBWriter with SQL connection details from .env"""
        self.sql_driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
        self.sql_server = os.getenv("SQL_SERVER", "localhost")
        self.sql_user = os.getenv("SQL_USER", "sa")
        self.sql_pass = os.getenv("SQL_PASS", "")
        self.sql_database = os.getenv("SQL_DATABASE", "solar")
        self.table_prefix = table_prefix
        self.conn_str = None
        
        # Cumulative energy tracking (for kWh calculations)
        self.cumulative = {
            "pv_power": 0.0,
            "grid_import": 0.0,
            "grid_export": 0.0,
            "battery_charge": 0.0,
            "battery_discharge": 0.0
        }
        
        # State change tracking (write only on change)
        self.last_state = {
            "inverter_state": None,
            "battery_mode": None,
        }

    def _build_conn_string(self):
        """Build ODBC connection string"""
        return (
            f"Driver={{{self.sql_driver}}};"
            f"Server={self.sql_server};"
            f"Database={self.sql_database};"
            f"UID={self.sql_user};"
            f"PWD={self.sql_pass};"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
        )

    def _connect(self):
        """Create and return a database connection"""
        if not self.conn_str:
            self.conn_str = self._build_conn_string()
        return pyodbc.connect(self.conn_str)

    def connect(self):
        """Test connection"""
        try:
            conn = self._connect()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def _update_cumulative(self, metric, kw, minutes):
        """Update cumulative energy: kW * (minutes / 60) = kWh"""
        if metric in self.cumulative:
            self.cumulative[metric] += kw * (minutes / 60.0)
            return self.cumulative[metric]
        return 0.0

    def write_1min(self, cache, minutes=1):
        """
        Write 1-minute snapshot from cache.
        Writes one row per NUMERIC metric with kW + cumulative_kwh.
        Non-numeric metrics (e.g., inverter_state, battery_mode) are skipped.
        summary_1min() returns {key: (value, timestamp)} tuples.
        """
        snapshot = cache.summary_1min()
        timestamp = datetime.now(UTC)
        
        sql = f"""
        INSERT INTO dbo.{self.table_prefix}summary_1min (timestamp, metric, kw, cumulative_kwh)
        VALUES (?, ?, ?, ?)
        """
        
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            # Write each NUMERIC metric (skip strings like inverter_state, battery_mode)
            for metric, value_tuple in snapshot.items():
                # Extract value from tuple (value, ts)
                value = value_tuple[0] if isinstance(value_tuple, tuple) else value_tuple
                
                if value is not None:
                    try:
                        kw_val = float(value) if isinstance(value, (int, float, str)) else 0.0
                        cumulative_kwh = self._update_cumulative(metric, kw_val, minutes)
                        cursor.execute(sql, timestamp, metric, kw_val, cumulative_kwh)
                    except (ValueError, TypeError):
                        # Skip non-numeric metrics (state info) - intentional
                        logger.debug(f"Skipped non-numeric metric '{metric}': {value}")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error writing 1min data: {e}")

    def write_15min(self, cache, minutes=15):
        """
        Write 15-minute snapshot from cache.
        Writes one row per NUMERIC metric with kW + cumulative_kwh.
        Non-numeric metrics (e.g., inverter_state, battery_mode) are skipped.
        summary_15min() returns {key: value} (already extracted from tuples).
        """
        snapshot = cache.summary_15min()
        timestamp = datetime.now(UTC)
        
        sql = f"""
        INSERT INTO dbo.{self.table_prefix}summary_15min (timestamp, metric, kw, cumulative_kwh)
        VALUES (?, ?, ?, ?)
        """
        
        try:
            conn = self._connect()
            cursor = conn.cursor()
            
            # Write each NUMERIC metric (skip strings like inverter_state, battery_mode)
            for metric, value in snapshot.items():
                if value is not None:
                    try:
                        kw_val = float(value) if isinstance(value, (int, float, str)) else 0.0
                        cumulative_kwh = self._update_cumulative(metric, kw_val, minutes)
                        cursor.execute(sql, timestamp, metric, kw_val, cumulative_kwh)
                    except (ValueError, TypeError):
                        # Skip non-numeric metrics (state info) - intentional
                        logger.debug(f"Skipped non-numeric metric '{metric}': {value}")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error writing 15min data: {e}")

    def write_daily(self, cache):
        """
        Write daily summary to summary_daily table.
        Extracts only NUMERIC energy metrics from cache (ignores state info).
        summary_daily() returns {key: value}.
        """
        snapshot = cache.summary_daily()
        summary_date = datetime.now(UTC).date()
        
        # Extract recorded values from cache (using 'today_*' fields)
        # Get values with fallback to 0 if not found or non-numeric
        try:
            recorded_pv_kwh = float(snapshot.get("today_pv_energy", 0) or 0)
            recorded_grid_import_kwh = float(snapshot.get("today_grid_import", 0) or 0)
            recorded_grid_export_kwh = float(snapshot.get("today_grid_export", 0) or 0)
            recorded_batt_charge_kwh = float(snapshot.get("today_batt_charge", 0) or 0)
            recorded_batt_discharge_kwh = float(snapshot.get("today_batt_discharge", 0) or 0)
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not convert daily snapshot values to float: {e}")
            return
        
        sql = f"""
        INSERT INTO dbo.{self.table_prefix}summary_daily 
            (summary_date, recorded_pv_kwh, recorded_grid_import_kwh, 
             recorded_grid_export_kwh, recorded_batt_charge_kwh, recorded_batt_discharge_kwh)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(sql, summary_date, recorded_pv_kwh, recorded_grid_import_kwh,
                          recorded_grid_export_kwh, recorded_batt_charge_kwh, recorded_batt_discharge_kwh)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error writing daily data: {e}")

    def write_state_changes(self, cache):
        """Write state changes only when values differ from last recorded state."""
        snapshot = cache.summary_1min()
        timestamp = datetime.now(UTC)
        
        state_metrics = {"inverter_state", "battery_mode"}
        state_records = []
        
        # Check each state metric for changes
        for metric in state_metrics:
            value_tuple = snapshot.get(metric)
            if value_tuple:
                # Extract value from tuple (value, ts)
                current_value = value_tuple[0] if isinstance(value_tuple, tuple) else value_tuple
                
                # Only record if different from last known state
                if current_value is not None and current_value != self.last_state[metric]:
                    state_records.append((metric, current_value))
                    self.last_state[metric] = current_value
                    logger.info(f"State change: {metric} = {current_value}")
        
        # Write all changes in one batch
        if state_records:
            sql = f"""
            INSERT INTO dbo.{self.table_prefix}inverter_state_changes (timestamp, state_key, state_value)
            VALUES (?, ?, ?)
            """
            
            try:
                conn = self._connect()
                cursor = conn.cursor()
                for metric, value in state_records:
                    cursor.execute(sql, timestamp, metric, value)
                conn.commit()
                conn.close()
                logger.debug(f"Wrote {len(state_records)} state change(s) to database")
            except Exception as e:
                logger.error(f"Error writing state changes: {e}")

    def log_freshness(self, event_type, max_age=None, min_age=None, metrics_checked=None, message=""):
        """
        Log data freshness event to database.
        
        Args:
            event_type: 'FRESH', 'STALE', or 'MQTT_ERROR'
            max_age: Age in seconds of oldest cached metric
            min_age: Age in seconds of newest cached metric
            metrics_checked: Number of metrics checked
            message: Additional message
        """
        sql = f"""
        INSERT INTO dbo.{self.table_prefix}data_freshness_log (timestamp, event_type, max_cache_age_seconds, min_cache_age_seconds, metrics_checked, message)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(sql, datetime.now(UTC), event_type, max_age, min_age, metrics_checked, message)
            conn.commit()
            conn.close()
            logger.debug(f"Logged freshness event: {event_type}")
        except Exception as e:
            logger.warning(f"Failed to log freshness event: {e}")
