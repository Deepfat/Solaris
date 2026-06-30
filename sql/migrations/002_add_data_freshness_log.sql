-- Migration 002: Add data freshness logging table
-- Purpose: Track MQTT staleness and connection issues
-- Safe to re-run (uses IF NOT EXISTS)

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'data_freshness_log')
BEGIN
    CREATE TABLE dbo.data_freshness_log (
        id INT IDENTITY(1,1) PRIMARY KEY,
        timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        event_type NVARCHAR(32) NOT NULL,  -- 'FRESH', 'STALE', 'MQTT_ERROR'
        max_cache_age_seconds INT,  -- Age of oldest metric in cache
        min_cache_age_seconds INT,  -- Age of newest metric in cache
        metrics_checked INT,  -- Total metrics in cache
        message NVARCHAR(512)
    );

    CREATE NONCLUSTERED INDEX idx_data_freshness_log_timestamp 
        ON dbo.data_freshness_log (timestamp DESC);

    CREATE NONCLUSTERED INDEX idx_data_freshness_log_event_type 
        ON dbo.data_freshness_log (event_type, timestamp DESC);

    PRINT 'Created data_freshness_log table'
END
ELSE
BEGIN
    PRINT 'data_freshness_log table already exists'
END
