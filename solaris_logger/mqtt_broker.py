# solaris_logger/mqtt_broker.py v8
# MQTT ingestion layer: loads settings from .env, connects to broker, receives JSON, updates cache.

import json
import os
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from solaris_logger.cache import TelemetryCache

# Load .env into environment
load_dotenv()


class MQTTBroker:
    def __init__(self, cache: TelemetryCache):
        self.host = os.getenv("MQTT_HOST", "localhost")
        self.port = int(os.getenv("MQTT_PORT", "1883"))
        self.topic = os.getenv("MQTT_TOPIC", "#")
        self.user = os.getenv("MQTT_USER", "")
        self.password = os.getenv("MQTT_PASS", "")
        self.cache = cache

        # Use modern callback API
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2
        )

        # Apply authentication if provided
        if self.user:
            self.client.username_pw_set(self.user, self.password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe(self.topic)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            return

        payload.pop("device_id", None)

        for field, value in payload.items():
            self.cache.update(field, value)

    def start(self):
        self.client.connect(self.host, self.port)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
