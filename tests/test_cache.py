# test_cache.py

import time
from solaris_logger.cache import TelemetryCache

def test_initial_state():
    cache = TelemetryCache()
    snap = cache.snapshot()

    # All fields should start as (None, None)
    for key, (value, ts) in snap.items():
        assert value is None
        assert ts is None


def test_update_and_snapshot():
    cache = TelemetryCache()

    cache.update("pv_power", 123)
    snap = cache.snapshot()

    value, ts = snap["pv_power"]
    assert value == 123
    assert isinstance(ts, float)


def test_thread_safety():
    cache = TelemetryCache()

    def writer():
        for _ in range(1000):
            cache.update("pv_power", 1)

    import threading
    threads = [threading.Thread(target=writer) for _ in range(10)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    value, ts = cache.snapshot()["pv_power"]
    assert value == 1
    assert isinstance(ts, float)
