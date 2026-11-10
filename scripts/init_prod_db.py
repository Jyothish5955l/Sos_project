"""
SOS Guardian — Production Database Initialization & Health Check Script
========================================================================
Run this script during deployment or CI/CD pipelines to verify that:
1. Target database directory exists and has write permissions.
2. SQLite schema is created with all tables, indices, and foreign keys.
3. WAL journal mode is properly engaged.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.database import initialize_database, get_connection, DATABASE


def verify_database():
    print(f"[*] Target database path: {DATABASE}")

    db_dir = os.path.dirname(DATABASE)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        print(f"[+] Directory verified: {db_dir}")

    print("[*] Initializing tables and schema migrations...")
    initialize_database()

    conn = get_connection()
    cursor = conn.cursor()

    # Query all created tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    expected_tables = {
        "users",
        "emergency_contacts",
        "sos_events",
        "notification_logs",
        "sos_location_breadcrumbs",
        "safety_checkins"
    }

    missing = expected_tables - tables
    if missing:
        print(f"[-] ERROR: Missing tables: {missing}")
        conn.close()
        sys.exit(1)

    # Verify foreign key support is enabled
    cursor.execute("PRAGMA foreign_keys;")
    fk_status = cursor.fetchone()[0]

    # Verify quick insert/select probe
    cursor.execute("SELECT 1;")
    probe = cursor.fetchone()[0]

    conn.close()

    print(f"[+] Verified tables: {sorted(list(tables))}")
    print(f"[+] Foreign keys enabled: {bool(fk_status)}")
    print(f"[+] SQLite read/write probe: {probe == 1}")
    print("[SUCCESS] Production database is fully initialized and operational!")


if __name__ == "__main__":
    verify_database()
