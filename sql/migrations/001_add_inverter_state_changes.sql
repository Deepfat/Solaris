-- Migration 001: Add inverter_state_changes table
-- Adds state tracking for inverter_state and battery_mode
-- Safe to run multiple times (uses IF NOT EXISTS)

USE [solar];
GO

-- Create schema version tracking table if it doesn't exist
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE name='_schema_version')
BEGIN
    CREATE TABLE dbo._schema_version (
        id INT IDENTITY(1,1) PRIMARY KEY,
        migration_name NVARCHAR(255) NOT NULL UNIQUE,
        applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END
GO

-- Add inverter_state_changes table if it doesn't exist
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE name='inverter_state_changes')
BEGIN
    CREATE TABLE dbo.inverter_state_changes (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        timestamp DATETIME2(0) NOT NULL,
        state_key NVARCHAR(64) NOT NULL,
        state_value NVARCHAR(255) NOT NULL
    );
    
    CREATE INDEX IX_inverter_state_changes_timestamp ON dbo.inverter_state_changes (timestamp);
    CREATE INDEX IX_inverter_state_changes_key ON dbo.inverter_state_changes (state_key, timestamp DESC);
END
GO

-- Create prune procedure (needs its own batch)
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE name='prune_inverter_state_changes' AND type='P')
BEGIN
    EXEC sp_executesql N'
        CREATE PROCEDURE dbo.prune_inverter_state_changes
        AS
        BEGIN
            SET NOCOUNT ON;
            DELETE FROM dbo.inverter_state_changes
            WHERE timestamp < DATEADD(year, -2, SYSUTCDATETIME());
        END;
    ';
END
GO

-- Mark this migration as applied
INSERT INTO dbo._schema_version (migration_name) 
SELECT '001_add_inverter_state_changes'
WHERE NOT EXISTS (SELECT 1 FROM dbo._schema_version WHERE migration_name='001_add_inverter_state_changes')
GO
