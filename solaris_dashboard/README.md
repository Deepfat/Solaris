# Solaris Dashboard

Real-time visualization of GivEnergy inverter telemetry from SQL Server.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r ../requirements.txt
```

### 2. Run Dashboard

```bash
python -m solaris_dashboard.app
```

Dashboard runs at: **http://localhost:8050**

## Features

- **Live Metrics** — PV Power, Battery Power, Grid Power, Battery SOC
- **Power Output Graph** — Real-time power flows (1H, 6H, 24H, 7D, 30D views)
- **Battery SOC Trend** — State of charge over time
- **Cumulative Energy** — kWh generation tracking
- **Data Freshness Audit** — MQTT staleness events
- **State Changes** — Inverter mode transitions

## Time Range Buttons

- **1H** — Last 1-minute readings (live)
- **6H** — Last 1-minute readings
- **24H** — Last 1-minute readings
- **7D** — Aggregated 15-minute readings
- **30D** — Daily aggregated readings

## Architecture

- `database.py` — SQL queries for all tables (summary_1min, summary_15min, etc.)
- `layout.py` — Dashboard UI components (Bootstrap grid, cards, graphs)
- `app.py` — Dash callbacks and update logic

## Database Tables Used

- `summary_1min` — Instantaneous power metrics (1-min intervals)
- `summary_15min` — Aggregated power (15-min intervals)
- `summary_daily` — Daily energy totals
- `inverter_state_changes` — Mode transitions (charging/discharging)
- `data_freshness_log` — MQTT staleness audit trail
