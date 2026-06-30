#!/usr/bin/env python
# mqtt_listener.py — Diagnostic tool to show all MQTT topics on broker
# Usage: python mqtt_listener.py
# Shows every message received so you can see what GivTCP is publishing

import os
import json
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("MQTT_HOST", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
USER = os.getenv("MQTT_USER", "")
PASS = os.getenv("MQTT_PASS", "")

client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, connect_flags, reason_code, properties):
    print(f"[*] Connected to {HOST}:{PORT} (reason: {reason_code})")
    print("[*] Subscribing to all topics (#)...")
    client.subscribe("#")

def on_message(client, userdata, msg):
    print(f"\n[TOPIC] {msg.topic}")
    print(f"[PAYLOAD] {msg.payload.decode('utf-8', errors='replace')[:200]}")

if USER:
    client.username_pw_set(USER, PASS)

client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to MQTT broker at {HOST}:{PORT}...")
client.connect(HOST, PORT)
client.loop_forever()
