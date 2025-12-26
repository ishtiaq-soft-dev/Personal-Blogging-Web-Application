"""
Migration script to add image column to comments table.
Run this script once to update the database schema.
"""
import sqlite3
import os

# Path to database
DB_PATH = os.path.join(os.path.dirname(__file__), 'blog.db')

def migrate():
    """Add image column to comments table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(comments)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'image' not in columns:
        print("Adding 'image' column to comments table...")
        cursor.execute("""
            ALTER TABLE comments
            ADD COLUMN image VARCHAR(255)
        """)
        conn.commit()
        print("✓ Column 'image' added successfully!")
    else:
        print("✓ Column 'image' already exists in comments table.")
    
    conn.close()
    print("\nMigration completed!")

if __name__ == '__main__':
    migrate()

