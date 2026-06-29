# tests/test_mqtt_broker.py v6
# Contains both a logic test (cache update) and a real MQTT connection test.

import time
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

from solaris_logger.cache import TelemetryCache
from solaris_logger.mqtt_broker import MQTTBroker

load_dotenv()


def test_message_updates_cache():
    cache = TelemetryCache()
    broker = MQTTBroker(cache)

    class FakeMsg:
        def __init__(self):
            self.payload = b'{"pv_power": 230}'

    broker._on_message(None, None, FakeMsg())

    value, ts = cache.snapshot()["pv_power"]
    assert value == 230
    assert ts is not None


def test_real_mqtt_connection():
    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    user = os.getenv("MQTT_USER", "")
    password = os.getenv("MQTT_PASS", "")

    connected = {"ok": False}

    # Correct API v2 signature: (client, userdata, flags, rc, properties)
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            connected["ok"] = True

    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

    if user:
        client.username_pw_set(user, password)

    client.on_connect = on_connect
    client.connect(host, port)
    client.loop_start()

    for _ in range(20):
        if connected["ok"]:
            break
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()

    assert connected["ok"], "Failed to connect to the MQTT broker"
