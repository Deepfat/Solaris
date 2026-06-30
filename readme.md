# Solaris

Telemetry pipeline: GivEnergy inverter → Home Assistant → MQTT → Python → SQL Server.

Captures inverter state from Mosquitto MQTT broker, maintains in-memory cache, writes snapshots and state changes to SQL Server.


## Architecture

```
GivEnergy Inverter → Home Assistant → MQTT Broker (Mosquitto)
                                           ↓
                        solaris_logger (Python pipeline)
                        ├─ MQTTBroker (subscribe, parse)
                        ├─ TelemetryCache (thread-safe state)
                        └─ DBWriter (write snapshots)
                                           ↓
                        SQL Server (solar database)
```

### Components

| Component | Purpose |
|-----------|---------|
| **MQTTBroker** | Subscribes to GivEnergy topics, parses JSON, updates cache |
| **TelemetryCache** | Thread-safe in-memory state (kW, SOC, cumulative energy, inverter state) |
| **DBWriter** | Reads cache, writes to SQL Server tables |

### Data Flow

1. **Numeric metrics** (power, SOC, energy): `cache → summary_1min, summary_15min, summary_daily`
2. **State changes** (inverter_state, battery_mode): `cache → inverter_state_changes` (on change only)

### Tables

| Table | Interval | Retention | Purpose |
|-------|----------|-----------|---------|
| `summary_1min` | 1 minute | 7 days | Instantaneous kW + cumulative kWh |
| `summary_15min` | 15 minutes | 6 months | Aggregated readings |
| `summary_daily` | Daily | Indefinite | Daily energy totals (upsert) |
| `inverter_state_changes` | On change | 2 years | State transitions only (no duplicate writes) |

### Scheduler

Trigger via Windows Task Scheduler or systemd cron:
- **1-min task**: `write_1min()` + `write_state_changes()`
- **15-min task**: `write_15min()`
- **Daily task**: `write_daily()` + `prune_summary_1min()` + `prune_summary_15min()`


## Setup

1. Create `.env`:
```
MQTT_HOST=<host>
MQTT_PORT=1883
MQTT_TOPIC=givenergy/#
MQTT_USER=<user>
MQTT_PASS=<pass>

SQL_DRIVER=ODBC Driver 18 for SQL Server
SQL_SERVER=<server>
SQL_USER=<user>
SQL_PASS=<pass>
SQL_DATABASE=solar
```

2. Fresh database:
```bash
sqlcmd -S <server> -U <user> -P <pass> -i sql/create_solar_db_schema.sql
```

3. Existing database (apply migrations):
```bash
python sql/apply_migrations.py
```

4. Run integration tests:
```bash
pytest tests/integration_test.py -v
```

Test data appears in `itest_*` tables for inspection in SSMS.


## Project Layout

```
solaris_logger/
    cache.py              # TelemetryCache
    mqtt_broker.py        # MQTTBroker
    db_writer.py          # DBWriter
sql/
    create_solar_db_schema.sql       # Fresh install
    apply_migrations.py              # Migration runner
    migrations/
        001_add_inverter_state_changes.sql
tests/
    integration_test.py              # Cache → DB end-to-end
.env                                 # Config (SQL + MQTT credentials)
```
