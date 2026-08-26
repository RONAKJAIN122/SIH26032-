"""
Reset Database for Live Testing & Clean Demos
Clears all mock bookings and payment logs while preserving Mandi centers and base demo farmer accounts.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "backend", "smartmandi.db")
db_path = os.path.abspath(db_path)

if not os.path.exists(db_path):
    print(f"[!] Database file not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Clear dynamic queue data
cur.execute("DELETE FROM payments")
cur.execute("DELETE FROM bookings")

# Reset auto-increment sequences for bookings and payments if sqlite_sequence exists
try:
    cur.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name IN ('bookings', 'payments')")
except Exception:
    pass

conn.commit()

# Print status
cur.execute("SELECT count(*) FROM centers")
centers_count = cur.fetchone()[0]

cur.execute("SELECT count(*) FROM farmers")
farmers_count = cur.fetchone()[0]

cur.execute("SELECT count(*) FROM bookings")
bookings_count = cur.fetchone()[0]

conn.close()

print("=" * 55)
print("  SmartMandi Clean Slate Demo Reset Complete")
print("=" * 55)
print(f"  Centers Available  : {centers_count}")
print(f"  Farmers in DB      : {farmers_count}")
print(f"  Active Bookings    : {bookings_count} (CLEAN QUEUE - 0)")
print("=" * 55)

