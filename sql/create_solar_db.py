# create_solar_db.py — atomic DB creation
# If schema creation fails, the DB is dropped.
# If DB already exists, script stops.

import os
import sys
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
SQL_SERVER = os.getenv("SQL_SERVER", "localhost")
SQL_USER   = os.getenv("SQL_USER", "")
SQL_PASS   = os.getenv("SQL_PASS", "")
SQL_TRUST  = os.getenv("SQL_TRUST_CERT", "yes")

SQL_DATABASE  = os.getenv("SQL_DATABASE", "solar")
SQL_MASTER_DB = os.getenv("SQL_MASTER_DATABASE", "master")

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "create_solar_db_schema.sql")


def build_conn_string(database):
    return (
        f"Driver={{{SQL_DRIVER}}};"
        f"Server={SQL_SERVER};"
        f"Database={database};"
        f"TrustServerCertificate={SQL_TRUST};"
        + (
            f"UID={SQL_USER};PWD={SQL_PASS};"
            if SQL_USER else
            "Trusted_Connection=yes;"
        )
    )


def connect_master():
    return pyodbc.connect(build_conn_string(SQL_MASTER_DB), autocommit=True)


def connect_target():
    return pyodbc.connect(build_conn_string(SQL_DATABASE))


def main():
    print(f"Connecting to SQL Server at {SQL_SERVER}...")

    master = connect_master()
    cur = master.cursor()

    # ------------------------------------------------------------
    # STOP if DB already exists
    # ------------------------------------------------------------
    cur.execute("SELECT name FROM sys.databases WHERE name = ?", SQL_DATABASE)
    if cur.fetchone():
        print(f"ERROR: Database '{SQL_DATABASE}' already exists. Aborting.")
        sys.exit(1)

    # ------------------------------------------------------------
    # Create DB
    # ------------------------------------------------------------
    print(f"Creating database '{SQL_DATABASE}'...")
    cur.execute(f"CREATE DATABASE [{SQL_DATABASE}]")
    print("Database created.")
    master.close()

    # ------------------------------------------------------------
    # Apply schema
    # ------------------------------------------------------------
    try:
        print("Connecting to new database...")
        db = connect_target()
        cur = db.cursor()

        print(f"Applying schema from {SCHEMA_FILE}...")
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            sql_script = f.read()

        sql_script = sql_script.replace("{{DB_NAME}}", SQL_DATABASE)

        for stmt in sql_script.split("GO"):
            s = stmt.strip()
            if s:
                cur.execute(s)
                db.commit()

        print("Solar DB created successfully.")
        db.close()

    except Exception as e:
        print("ERROR during schema creation:", e)

        # IMPORTANT: close connection BEFORE dropping DB
        try:
            db.close()
        except:
            pass

        print("Dropping database to maintain atomic behaviour...")

        master = connect_master()
        cur = master.cursor()
        cur.execute(
            f"ALTER DATABASE [{SQL_DATABASE}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;"
        )
        cur.execute(f"DROP DATABASE [{SQL_DATABASE}]")
        master.close()

        print("Database dropped due to failure.")
        sys.exit(1)


if __name__ == "__main__":
    main()
