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

    def check_freshness(self, max_age_seconds=300):
        """
        Check if cache data is recent enough to write to DB.
        
        Args:
            max_age_seconds: Maximum acceptable age of oldest metric (default 5 min)
        
        Returns:
            (is_fresh: bool, max_age: int, min_age: int, metrics_checked: int)
        """
        now = time.time()
        with self._lock:
            ages = []
            for metric, (value, ts) in self._data.items():
                if ts is not None:
                    age = now - ts
                    ages.append(age)
        
        if not ages:
            return False, None, None, len(self._data)
        
        max_age = max(ages)
        min_age = min(ages)
        is_fresh = max_age <= max_age_seconds
        
        return is_fresh, int(max_age), int(min_age), len(ages)

