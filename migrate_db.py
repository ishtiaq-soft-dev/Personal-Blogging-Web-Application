"""
Database Migration Script
Adds parent_comment_id column to comments table and creates comment_likes table
"""
import sqlite3
from pathlib import Path
from config import Config

def migrate_database():
    """Migrate the database to add hierarchical comments support"""
    config = Config()
    db_path = config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    
    print(f"Connecting to database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if parent_comment_id column exists
        cursor.execute("PRAGMA table_info(comments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'parent_comment_id' not in columns:
            print("Adding parent_comment_id column to comments table...")
            cursor.execute("""
                ALTER TABLE comments 
                ADD COLUMN parent_comment_id INTEGER
            """)
            print("[OK] Added parent_comment_id column")
        else:
            print("[OK] parent_comment_id column already exists")
        
        # Check if comment_likes table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='comment_likes'
        """)
        
        if not cursor.fetchone():
            print("Creating comment_likes table...")
            cursor.execute("""
                CREATE TABLE comment_likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id INTEGER NOT NULL,
                    user_identifier VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (comment_id) REFERENCES comments(id),
                    UNIQUE(comment_id, user_identifier)
                )
            """)
            print("[OK] Created comment_likes table")
        else:
            print("[OK] comment_likes table already exists")
        
        conn.commit()
        print("\n[OK] Database migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == '__main__':
    print("=" * 50)
    print("Database Migration Script")
    print("=" * 50)
    print()
    
    if migrate_database():
        print("\nMigration completed. You can now run your Flask app.")
    else:
        print("\nMigration failed. Please check the errors above.")

