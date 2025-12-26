"""
Database Migration Script for User Authentication
Adds users table and updates likes/comments to use user_id
"""
import sqlite3
from pathlib import Path
from config import Config

def migrate_database():
    """Migrate the database to add user authentication support"""
    config = Config()
    db_path = config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    
    print(f"Connecting to database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        if not cursor.fetchone():
            print("Creating users table...")
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(80) NOT NULL UNIQUE,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100),
                    created_at DATETIME NOT NULL
                )
            """)
            print("[OK] Created users table")
        else:
            print("[OK] users table already exists")
        
        # Check if user_id column exists in comments table
        cursor.execute("PRAGMA table_info(comments)")
        comments_columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in comments_columns:
            print("Adding user_id column to comments table...")
            cursor.execute("ALTER TABLE comments ADD COLUMN user_id INTEGER REFERENCES users(id)")
            print("[OK] Added user_id column to comments")
        else:
            print("[OK] user_id column already exists in comments")
        
        # Check if user_id column exists in likes table
        cursor.execute("PRAGMA table_info(likes)")
        likes_columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in likes_columns:
            print("Adding user_id column to likes table...")
            cursor.execute("ALTER TABLE likes ADD COLUMN user_id INTEGER REFERENCES users(id)")
            print("[OK] Added user_id column to likes")
            
            # Drop old unique constraint and create new one
            try:
                cursor.execute("DROP INDEX unique_like")
            except:
                pass
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS unique_like 
                ON likes(post_id, user_id)
            """)
        else:
            print("[OK] user_id column already exists in likes")
        
        # Check if user_id column exists in comment_likes table
        cursor.execute("PRAGMA table_info(comment_likes)")
        comment_likes_columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in comment_likes_columns:
            print("Adding user_id column to comment_likes table...")
            cursor.execute("ALTER TABLE comment_likes ADD COLUMN user_id INTEGER REFERENCES users(id)")
            print("[OK] Added user_id column to comment_likes")
            
            # Drop old unique constraint and create new one
            try:
                cursor.execute("DROP INDEX unique_comment_like")
            except:
                pass
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS unique_comment_like 
                ON comment_likes(comment_id, user_id)
            """)
        else:
            print("[OK] user_id column already exists in comment_likes")
        
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
    print("User Authentication Migration Script")
    print("=" * 50)
    print()
    
    if migrate_database():
        print("\nMigration completed. You can now run your Flask app.")
    else:
        print("\nMigration failed. Please check the errors above.")

