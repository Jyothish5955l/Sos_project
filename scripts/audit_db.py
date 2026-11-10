import sqlite3

conn = sqlite3.connect('data/sos_guardian.db')
cursor = conn.cursor()

cursor.execute('PRAGMA foreign_keys;')
print('PRAGMA foreign_keys default setting:', cursor.fetchone()[0])

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print('Tables in DB:', tables)

for t in tables:
    print(f"\n=== TABLE: {t} ===")
    cursor.execute(f"PRAGMA table_info({t});")
    for col in cursor.fetchall():
        print(f"  col: {col[1]} ({col[2]}), notnull={col[3]}, default={col[4]}, pk={col[5]}")
    cursor.execute(f"PRAGMA foreign_key_list({t});")
    fks = cursor.fetchall()
    if fks:
        print("  Foreign keys:", fks)
    cursor.execute(f"SELECT COUNT(*) FROM {t};")
    print(f"  Row count: {cursor.fetchone()[0]}")

conn.close()
