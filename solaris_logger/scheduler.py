#!/usr/bin/env python
# scheduler.py — Entry point for Windows Task Scheduler
# Usage: python scheduler.py --mode 1min|15min|daily
# 
# For each mode:
#   1min: Subscribe to MQTT for 30s, write_1min(), write_state_changes()
#   15min: Subscribe to MQTT for 30s, write_15min()
#   daily: Subscribe to MQTT for 30s, write_daily()

import argparse
import logging
import sys
import time
from threading import Event

from solaris_logger.cache import TelemetryCache
from solaris_logger.mqtt_broker import MQTTBroker
from solaris_logger.db_writer import DBWriter

# Configure logging (writes to console + optional file)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def run_scheduler(mode: str, mqtt_timeout: int = 30) -> int:
    """
    Run scheduled task.
    
    Args:
        mode: "1min", "15min", or "daily"
        mqtt_timeout: seconds to wait for MQTT data before giving up
    
    Returns:
        0 on success, 1 on error
    """
    try:
        # Initialize cache and MQTT broker
        cache = TelemetryCache()
        mqtt = MQTTBroker(cache)
        writer = DBWriter()
        
        logger.info(f"Starting {mode} task...")
        
        # Connect to MQTT and wait for data
        try:
            mqtt.start()
            logger.info(f"Waiting {mqtt_timeout}s for MQTT data...")
            time.sleep(mqtt_timeout)
            mqtt.stop()
        except Exception as mqtt_err:
            logger.warning(f"MQTT connection failed: {mqtt_err}. Proceeding with cached data.")
            # Continue anyway — cache may have data from previous run
        
        # Check cache freshness (default max age: 5 minutes)
        MAX_CACHE_AGE = 300  # seconds
        is_fresh, max_age, min_age, metrics_checked = cache.check_freshness(MAX_CACHE_AGE)
        
        if not is_fresh:
            msg = f"Cache stale: {max_age}s old (max {MAX_CACHE_AGE}s)"
            logger.warning(msg)
            writer.log_freshness("STALE", max_age=max_age, min_age=min_age, metrics_checked=metrics_checked, message=msg)
            logger.info(f"{mode} task skipped (stale data)")
            return 0
        
        # Cache is fresh - proceed with writes
        writer.log_freshness("FRESH", max_age=max_age, min_age=min_age, metrics_checked=metrics_checked, 
                           message=f"Cache fresh: {max_age}s old")
        
        # Write to database based on mode
        if mode == "1min":
            logger.info("Writing 1-minute summary...")
            writer.write_1min(cache)
            writer.write_state_changes(cache)
        
        elif mode == "15min":
            logger.info("Writing 15-minute summary...")
            writer.write_15min(cache)
        
        elif mode == "daily":
            logger.info("Writing daily summary...")
            writer.write_daily(cache)
        
        else:
            logger.error(f"Unknown mode: {mode}")
            return 1
        
        logger.info(f"{mode} task completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error in {mode} task: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solaris scheduler entry point")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["1min", "15min", "daily"],
        help="Scheduled task mode"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="MQTT connection timeout in seconds (default: 30)"
    )
    
    args = parser.parse_args()
    exit_code = run_scheduler(args.mode, args.timeout)
    sys.exit(exit_code)
