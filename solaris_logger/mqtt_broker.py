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
        if reason_code == 0:
            logger.info(f"MQTT connected. Subscribing to topic: {self.topic}")
            client.subscribe(self.topic)
        else:
            logger.error(f"MQTT connection failed with code {reason_code}")

    def _on_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        logger.debug(f"MQTT message received on {msg.topic}: {msg.payload[:100]}")
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {msg.topic}: {e}")
            return
        
        # Handle both scalar values and JSON objects
        if isinstance(payload, dict):
            # JSON object — extract fields
            payload.pop("device_id", None)
            for field, value in payload.items():
                self.cache.update(field, value)
                logger.debug(f"Cache updated: {field} = {value}")
        else:
            # Scalar value (float, int, string) — use topic name as field
            # e.g., GivEnergy/.../raw/invertor/i_battery -> i_battery
            field = msg.topic.split("/")[-1]
            
            # Map GivEnergy field names to cache keys
            field_mapping = {
                # Power measurements
                "PV_Power": "pv_power",
                "Grid_Power": "grid_power",
                "Invertor_Power": "battery_power",  # Close estimate
                "EPS_Power": "load_power",  # Load power from EPS
                "Import_Power": "grid_import",
                "Export_Power": "grid_export",
                
                # Battery
                "Battery_SOC": "soc",
                "f_soc": "soc",
                
                # State
                "inverter_status": "inverter_state",
                "Invertor_Status": "inverter_state",
                "battery_mode": "battery_mode",
                
                # Energy totals
                "Today_PV_Energy": "today_pv_energy",
                "Today_Export_Energy": "today_grid_export",
                "Today_Import_Energy": "today_grid_import",
                "Today_Battery_Charge_Energy": "today_batt_charge",
                "Today_Battery_Discharge_Energy": "today_batt_discharge",
                "Today_Load_Energy": "today_load_energy",
            }
            
            mapped_field = field_mapping.get(field, field)  # Use mapping if exists, else original
            
            # Only update if we recognize the field
            if mapped_field in ["pv_power", "grid_power", "battery_power", "load_power", "soc", "inverter_state", "battery_mode", "grid_import", "grid_export", "today_pv_energy", "today_grid_export", "today_grid_import", "today_batt_charge", "today_batt_discharge", "today_load_energy"]:
                self.cache.update(mapped_field, payload)
                logger.debug(f"Cache updated: {mapped_field} = {payload}")

    def start(self):
        self.client.connect(self.host, self.port)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
