# cache.py v4
# Unified telemetry cache with 1‑min, 15‑min and daily summaries

import threading
import time

class TelemetryCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            "pv_power": (None, None),
            "grid_power": (None, None),
            "battery_power": (None, None),
            "load_power": (None, None),
            "soc": (None, None),
            "inverter_state": (None, None),
            "battery_mode": (None, None),
            "today_pv_energy": (None, None),
            "today_grid_import": (None, None),
            "today_grid_export": (None, None),
            "today_batt_charge": (None, None),
            "today_batt_discharge": (None, None),
            "today_load_energy": (None, None),
        }

    def update(self, key, value):
        ts = time.time()
        with self._lock:
            if key in self._data:
                self._data[key] = (value, ts)

    def summary_1min(self):
        with self._lock:
            return dict(self._data)

    def summary_15min(self):
        with self._lock:
            return {k: v for k, (v, _) in self._data.items()}

    def summary_daily(self):
        with self._lock:
            return {k: v for k, (v, _) in self._data.items()}
