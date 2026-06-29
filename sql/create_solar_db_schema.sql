------------------------------------------------------------
-- create_solar_db_schema.sql v15
-- SI-clean schema: instantaneous kW + cumulative kWh
------------------------------------------------------------

USE [solar];
GO

------------------------------------------------------------
-- 1-MIN SUMMARY TABLE
------------------------------------------------------------
CREATE TABLE dbo.summary_1min (
    id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    timestamp DATETIME2(0) NOT NULL,
    metric NVARCHAR(64) NOT NULL,
    kw FLOAT NULL,
    cumulative_kwh FLOAT NULL
);
GO

CREATE INDEX IX_summary_1min_timestamp ON dbo.summary_1min (timestamp);
CREATE INDEX IX_summary_1min_metric    ON dbo.summary_1min (metric);
GO

------------------------------------------------------------
-- 15-MIN SUMMARY TABLE
------------------------------------------------------------
CREATE TABLE dbo.summary_15min (
    id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    timestamp DATETIME2(0) NOT NULL,
    metric NVARCHAR(64) NOT NULL,
    kw FLOAT NULL,
    cumulative_kwh FLOAT NULL
);
GO

CREATE INDEX IX_summary_15min_timestamp ON dbo.summary_15min (timestamp);
CREATE INDEX IX_summary_15min_metric    ON dbo.summary_15min (metric);
GO

------------------------------------------------------------
-- DAILY SUMMARY TABLE (NO max_* columns)
------------------------------------------------------------
CREATE TABLE dbo.summary_daily (
    summary_date DATE NOT NULL PRIMARY KEY,

    recorded_pv_kwh FLOAT NULL,
    recorded_grid_import_kwh FLOAT NULL,
    recorded_grid_export_kwh FLOAT NULL,
    recorded_batt_charge_kwh FLOAT NULL,
    recorded_batt_discharge_kwh FLOAT NULL,

    calc_pv_kwh FLOAT NULL,
    calc_grid_import_kwh FLOAT NULL,
    calc_grid_export_kwh FLOAT NULL,
    calc_batt_charge_kwh FLOAT NULL,
    calc_batt_discharge_kwh FLOAT NULL,

    calc_timestamp DATETIME2 NULL,
    repaired_flag BIT NOT NULL DEFAULT 0
);
GO

CREATE INDEX IX_summary_daily_date ON dbo.summary_daily (summary_date);
GO

------------------------------------------------------------
-- PRUNE PROCEDURE: 1-MIN SUMMARY
------------------------------------------------------------
CREATE PROCEDURE dbo.prune_summary_1min
AS
BEGIN
    SET NOCOUNT ON;
    DELETE FROM dbo.summary_1min
    WHERE timestamp < DATEADD(day, -7, SYSUTCDATETIME());
END;
GO

------------------------------------------------------------
-- PRUNE PROCEDURE: 15-MIN SUMMARY
------------------------------------------------------------
CREATE PROCEDURE dbo.prune_summary_15min
AS
BEGIN
    SET NOCOUNT ON;
    DELETE FROM dbo.summary_15min
    WHERE timestamp < DATEADD(month, -6, SYSUTCDATETIME());
END;
GO

------------------------------------------------------------
-- DAILY COMPUTATION PROCEDURE (NO max_* logic)
------------------------------------------------------------
CREATE PROCEDURE dbo.compute_daily_from_1min
    @target_date DATE
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @pv_kwh FLOAT;
    DECLARE @grid_imp_kwh FLOAT;
    DECLARE @grid_exp_kwh FLOAT;
    DECLARE @batt_chg_kwh FLOAT;
    DECLARE @batt_dis_kwh FLOAT;

    ;WITH day_data AS (
        SELECT *
        FROM dbo.summary_1min
        WHERE CAST(timestamp AS DATE) = @target_date
    )
    SELECT
        @pv_kwh =
            MAX(CASE WHEN metric='pv_power' THEN cumulative_kwh END)
            - MIN(CASE WHEN metric='pv_power' THEN cumulative_kwh END),

        @grid_imp_kwh =
            MAX(CASE WHEN metric='grid_import' THEN cumulative_kwh END)
            - MIN(CASE WHEN metric='grid_import' THEN cumulative_kwh END),

        @grid_exp_kwh =
            MAX(CASE WHEN metric='grid_export' THEN cumulative_kwh END)
            - MIN(CASE WHEN metric='grid_export' THEN cumulative_kwh END),

        @batt_chg_kwh =
            MAX(CASE WHEN metric='battery_charge' THEN cumulative_kwh END)
            - MIN(CASE WHEN metric='battery_charge' THEN cumulative_kwh END),

        @batt_dis_kwh =
            MAX(CASE WHEN metric='battery_discharge' THEN cumulative_kwh END)
            - MIN(CASE WHEN metric='battery_discharge' THEN cumulative_kwh END)
    FROM day_data;

    UPDATE dbo.summary_daily
    SET
        calc_pv_kwh             = @pv_kwh,
        calc_grid_import_kwh    = @grid_imp_kwh,
        calc_grid_export_kwh    = @grid_exp_kwh,
        calc_batt_charge_kwh    = @batt_chg_kwh,
        calc_batt_discharge_kwh = @batt_dis_kwh,
        calc_timestamp          = SYSUTCDATETIME(),
        repaired_flag           = 1
    WHERE summary_date = @target_date;
END;
GO
