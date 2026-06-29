# db_writer.py — Solaris v15
# Writes 1‑min, 15‑min and daily summary rows.
# Python computes cumulative_kwh; SQL handles daily totals.

import pyodbc

class DBWriter:
    def __init__(self, conn_str, table_prefix=""):
        self.conn_str = conn_str
        self.table_prefix = table_prefix

        # cumulative state held in memory
        self.cumulative = {
            "pv_power": 0.0,
            "grid_import": 0.0,
            "grid_export": 0.0,
            "battery_charge": 0.0,
            "battery_discharge": 0.0
        }

    def _connect(self):
        return pyodbc.connect(self.conn_str)

    def _update_cumulative(self, metric, kw, minutes):
        # energy = power * time
        # kw * (minutes / 60)
        self.cumulative[metric] += kw * (minutes / 60.0)
        return self.cumulative[metric]

    def write_1min(self, timestamp, metric, kw):
        cumulative_kwh = self._update_cumulative(metric, kw, 1)

        sql = f"""
        INSERT INTO {self.table_prefix}summary_1min (timestamp, metric, kw, cumulative_kwh)
        VALUES (?, ?, ?, ?)
        """

        with self._connect() as conn:
            conn.execute(sql, timestamp, metric, kw, cumulative_kwh)
            conn.commit()

    def write_15min(self, timestamp, metric, kw):
        cumulative_kwh = self._update_cumulative(metric, kw, 15)

        sql = f"""
        INSERT INTO {self.table_prefix}summary_15min (timestamp, metric, kw, cumulative_kwh)
        VALUES (?, ?, ?, ?)
        """

        with self._connect() as conn:
            conn.execute(sql, timestamp, metric, kw, cumulative_kwh)
            conn.commit()

    def write_daily(self, summary_date,
                    recorded_pv_kwh,
