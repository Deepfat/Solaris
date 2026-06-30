# solaris_logger/mqtt_broker.py v9
# MQTT ingestion layer: loads settings from .env, connects to broker, receives JSON, updates cache.

import json
import os
import logging
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from solaris_logger.cache import TelemetryCache

# Load .env into environment
load_dotenv()

logger = logging.getLogger(__name__)


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

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        """Callback when MQTT client connects (VERSION2 signature)"""
        print(f"[MQTT_CALLBACK] _on_connect called with reason_code={reason_code}")
        if reason_code == 0:
            print(f"[MQTT_CALLBACK] Subscribing to topic: {self.topic}")
            logger.info(f"MQTT connected. Subscribing to topic: {self.topic}")
            client.subscribe(self.topic)
        else:
            logger.error(f"MQTT connection failed with code {reason_code}")

    def _on_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        print(f"[MQTT_CALLBACK] Message received on {msg.topic}")
        logger.debug(f"MQTT message received on {msg.topic}: {msg.payload[:100]}")
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {msg.topic}: {e}")
            return

        payload.pop("device_id", None)

        for field, value in payload.items():
            self.cache.update(field, value)
            logger.debug(f"Cache updated: {field} = {value}")

    def start(self):
        self.client.connect(self.host, self.port)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
