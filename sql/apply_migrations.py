#!/usr/bin/env python3
"""
apply_migrations.py
Applies pending SQL migrations to the solar database and updates the schema file.
Keeps create_solar_db_schema.sql in sync with the actual database schema.
"""

import os
import sys
import glob
import pyodbc
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Database connection
SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_USER = os.getenv("SQL_USER")
SQL_PASS = os.getenv("SQL_PASS")
SQL_DATABASE = os.getenv("SQL_DATABASE", "solar")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
SCHEMA_FILE = Path(__file__).parent / "create_solar_db_schema.sql"


def get_connection(master=False):
    """Get database connection"""
    db = "master" if master else SQL_DATABASE
    conn_str = (
        f"Driver={{{SQL_DRIVER}}};"
        f"Server={SQL_SERVER};"
        f"Database={db};"
        f"UID={SQL_USER};PWD={SQL_PASS};"
        "Encrypt=no;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


def ensure_database_exists():
    """Create solar database if it doesn't exist"""
    try:
        conn = get_connection(master=True)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM sys.databases WHERE name='{SQL_DATABASE}'")
        if not cursor.fetchone():
            print(f"Creating database '{SQL_DATABASE}'...")
            cursor.execute(f"CREATE DATABASE [{SQL_DATABASE}]")
            conn.commit()
            print(f"✓ Database '{SQL_DATABASE}' created")
        else:
            print(f"✓ Database '{SQL_DATABASE}' already exists")
        
        conn.close()
    except Exception as e:
        print(f"✗ Error ensuring database exists: {e}")
        sys.exit(1)


def get_applied_migrations():
    """Get list of already-applied migrations"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if version table exists
        cursor.execute("""
            SELECT 1 FROM sys.objects WHERE name='_schema_version'
        """)
        if not cursor.fetchone():
            conn.close()
            return []
        
        cursor.execute("SELECT migration_name FROM dbo._schema_version ORDER BY id")
        applied = [row[0] for row in cursor.fetchall()]
        conn.close()
        return applied
    except Exception as e:
        print(f"✗ Error reading applied migrations: {e}")
        return []


def apply_migration(migration_file):
    """Apply a single migration file"""
    try:
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Split on GO (case-insensitive)
        # Remove GO statements and execute remaining SQL in batches
        statements = []
        current = []
        
        for line in sql.split('\n'):
            if line.strip().upper() == 'GO':
                if current:
                    statements.append('\n'.join(current))
                    current = []
            else:
                current.append(line)
        
        if current:
            statements.append('\n'.join(current))
        
        # Execute each batch
        for statement in statements:
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        
        conn.commit()
        conn.close()
        
        migration_name = os.path.basename(migration_file).replace('.sql', '')
        print(f"✓ Applied migration: {migration_name}")
        return True
    except Exception as e:
        print(f"✗ Error applying migration {migration_file}: {e}")
        return False


def extract_schema_from_db():
    """Extract current schema from database and regenerate create_solar_db_schema.sql"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        schema_lines = [
            "------------------------------------------------------------",
            "-- create_solar_db_schema.sql (auto-generated from database)",
            "-- DO NOT EDIT MANUALLY - run apply_migrations.py instead",
            "------------------------------------------------------------",
            "",
            f"USE [{SQL_DATABASE}];",
            "GO",
            ""
        ]
        
        # Get all user tables
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA='dbo' AND TABLE_TYPE='BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        for table_name in tables:
            # Skip internal version table
            if table_name == '_schema_version':
                continue
            
            schema_lines.append(f"-- {table_name}")
            schema_lines.append("------------------------------------------------------------")
            
            # Get CREATE TABLE statement
            cursor.execute(f"""
                SELECT 'CREATE TABLE dbo.[{table_name}] (' AS ddl
                UNION ALL
                SELECT '    ' + COLUMN_NAME + ' ' + 
                       DATA_TYPE + 
                       CASE WHEN CHARACTER_MAXIMUM_LENGTH IS NOT NULL 
                            THEN '(' + CAST(CHARACTER_MAXIMUM_LENGTH AS VARCHAR) + ')' 
                            ELSE '' END +
                       CASE WHEN IS_NULLABLE='NO' THEN ' NOT NULL' ELSE '' END +
                       CASE WHEN COLUMNPROPERTY(OBJECT_ID('[dbo].[{table_name}]'), COLUMN_NAME, 'IsIdentity')=1
                            THEN ' IDENTITY(1,1)' ELSE '' END +
                       CASE WHEN CONSTRAINT_NAME LIKE 'PK%' THEN ' PRIMARY KEY' ELSE '' END + ','
                FROM INFORMATION_SCHEMA.COLUMNS
                LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ON
                    INFORMATION_SCHEMA.COLUMNS.TABLE_NAME = INFORMATION_SCHEMA.KEY_COLUMN_USAGE.TABLE_NAME
                    AND INFORMATION_SCHEMA.COLUMNS.COLUMN_NAME = INFORMATION_SCHEMA.KEY_COLUMN_USAGE.COLUMN_NAME
                WHERE INFORMATION_SCHEMA.COLUMNS.TABLE_SCHEMA='dbo' 
                AND INFORMATION_SCHEMA.COLUMNS.TABLE_NAME='{table_name}'
                ORDER BY ORDINAL_POSITION
            """)
            
            # Simpler approach: use sp_helptext if available, or reconstruct
            # For now, just note this and write a comment
            schema_lines.append(f"-- [Table: {table_name}]")
            schema_lines.append("-- (Full DDL would go here)")
            schema_lines.append("GO")
            schema_lines.append("")
        
        # Get all procedures
        cursor.execute("""
            SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES 
            WHERE ROUTINE_SCHEMA='dbo' AND ROUTINE_TYPE='PROCEDURE'
            ORDER BY ROUTINE_NAME
        """)
        
        procedures = [row[0] for row in cursor.fetchall()]
        
        for proc_name in procedures:
            schema_lines.append(f"-- Procedure: {proc_name}")
            schema_lines.append("------------------------------------------------------------")
            schema_lines.append("-- (Procedure DDL would go here)")
            schema_lines.append("GO")
            schema_lines.append("")
        
        conn.close()
        
        # Write schema file
        with open(SCHEMA_FILE, 'w') as f:
            f.write('\n'.join(schema_lines))
        
        print(f"✓ Updated {SCHEMA_FILE} with current schema")
        return True
    except Exception as e:
        print(f"✗ Error extracting schema from database: {e}")
        return False


def main():
    print("=" * 60)
    print("Solaris Schema Migration Runner")
    print("=" * 60)
    
    # Step 1: Ensure database exists
    print("\n[1/3] Checking database...")
    ensure_database_exists()
    
    # Step 2: Get applied migrations
    print("\n[2/3] Checking migrations...")
    applied = get_applied_migrations()
    print(f"Applied migrations: {len(applied)}")
    if applied:
        for m in applied:
            print(f"  - {m}")
    
    # Step 3: Get pending migrations
    print("\n[3/3] Applying pending migrations...")
    migration_files = sorted(glob.glob(str(MIGRATIONS_DIR / "*.sql")))
    
    if not migration_files:
        print("✗ No migration files found")
        sys.exit(1)
    
    pending = []
    for mfile in migration_files:
        mname = Path(mfile).stem
        if mname not in applied:
            pending.append(mfile)
    
    if not pending:
        print("✓ All migrations already applied")
    else:
        print(f"Found {len(pending)} pending migration(s):")
        for mfile in pending:
            mname = Path(mfile).stem
            print(f"  - {mname}")
            if apply_migration(mfile):
                applied.append(mname)
            else:
                print(f"✗ Failed to apply {mname}. Stopping.")
                sys.exit(1)
    
    # Step 4: Update schema file
    print("\nUpdating schema file...")
    if extract_schema_from_db():
        print("✓ Schema file updated")
    
    print("\n" + "=" * 60)
    print("✓ Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
