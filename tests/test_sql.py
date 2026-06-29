# test_sql_connection.py — pytest version

import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def test_sql_connection():
    SQL_DRIVER   = os.getenv("SQL_DRIVER")
    SQL_SERVER   = os.getenv("SQL_SERVER")
    SQL_USER     = os.getenv("SQL_USER")
    SQL_PASS     = os.getenv("SQL_PASS")
    SQL_DATABASE = os.getenv("SQL_DATABASE")

    conn_str = (
        f"Driver={{{SQL_DRIVER}}};"
        f"Server={SQL_SERVER};"
        f"Database={SQL_DATABASE};"
        f"UID={SQL_USER};PWD={SQL_PASS};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )

    print("\n=== CONNECTION STRING ===")
    print(conn_str)
    print("=========================\n")

    try:
        conn = pyodbc.connect(conn_str)
        conn.close()
    except Exception as e:
        assert False, f"SQL connection failed: {e}"
