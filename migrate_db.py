"""
Database Migration Script
Adds new columns to existing database tables
"""

import sqlite3
import os

db_path = 'instance/pneumonia.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    print("No migration needed - new database will be created automatically")
    exit(0)

print("Migrating database schema...")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if columns exist and add them if they don't
try:
    # Add age column to patient table
    cursor.execute("ALTER TABLE patient ADD COLUMN age INTEGER")
    print("✓ Added 'age' column to patient table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("  'age' column already exists")
    else:
        print(f"  Error adding 'age': {e}")

try:
    # Add gender column to patient table
    cursor.execute("ALTER TABLE patient ADD COLUMN gender VARCHAR(20)")
    print("✓ Added 'gender' column to patient table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("  'gender' column already exists")
    else:
        print(f"  Error adding 'gender': {e}")

try:
    # Add gradcam_image column to prediction table
    cursor.execute("ALTER TABLE prediction ADD COLUMN gradcam_image TEXT")
    print("✓ Added 'gradcam_image' column to prediction table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("  'gradcam_image' column already exists")
    else:
        print(f"  Error adding 'gradcam_image': {e}")

conn.commit()
conn.close()

print("\n✅ Database migration complete!")
print("You can now restart the server.")
