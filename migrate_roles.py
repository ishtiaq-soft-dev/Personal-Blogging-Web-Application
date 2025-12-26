"""
Database Migration Script: Add Role-Based Authentication

This script:
1. Adds 'role' column to the users table
2. Sets default role to 'user' for existing users  
3. Migrates existing admins from the 'admin' table to 'users' table with role='admin'
4. Ensures no data loss and maintains backward compatibility

Run this script once to migrate your database:
    python migrate_roles.py
"""

import sys
from app import create_app
from extensions import db
from sqlalchemy import text, inspect

def migrate_roles():
    """Perform the role migration"""
    app = create_app()
    
    with app.app_context():
        conn = db.engine.connect()
        inspector = inspect(db.engine)
        
        try:
            # Step 1: Check if role column exists in users table
            users_columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'role' not in users_columns:
                print("Step 1: Adding 'role' column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL"))
                conn.commit()
                print("  ✓ Role column added successfully")
            else:
                print("Step 1: Role column already exists in users table")
            
            # Step 2: Set default role for existing users without role
            print("\nStep 2: Ensuring all existing users have 'user' role...")
            conn.execute(text("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''"))
            conn.commit()
            print("  ✓ Default roles set for existing users")
            
            # Step 3: Check if admin table exists and has records
            tables = inspector.get_table_names()
            
            if 'admin' in tables:
                print("\nStep 3: Migrating admins from 'admin' table to 'users' table...")
                
                # Get all admins
                result = conn.execute(text("SELECT id, username, password_hash, created_at FROM admin"))
                admins = result.fetchall()
                
                migrated_count = 0
                skipped_count = 0
                
                for admin in admins:
                    admin_id, username, password_hash, created_at = admin
                    
                    # Check if username already exists in users table
                    existing = conn.execute(
                        text("SELECT id FROM users WHERE username = :username"),
                        {"username": username}
                    ).fetchone()
                    
                    if existing:
                        # Update existing user to admin role
                        conn.execute(
                            text("UPDATE users SET role = 'admin' WHERE username = :username"),
                            {"username": username}
                        )
                        print(f"  → Updated existing user '{username}' to admin role")
                        migrated_count += 1
                    else:
                        # Create new user with admin role
                        # Generate a placeholder email for admins
                        admin_email = f"{username}@admin.local"
                        conn.execute(
                            text("""
                                INSERT INTO users (username, email, password_hash, role, created_at)
                                VALUES (:username, :email, :password_hash, 'admin', :created_at)
                            """),
                            {
                                "username": username,
                                "email": admin_email,
                                "password_hash": password_hash,
                                "created_at": created_at
                            }
                        )
                        print(f"  → Migrated admin '{username}' to users table")
                        migrated_count += 1
                
                conn.commit()
                print(f"\n  ✓ Migration complete: {migrated_count} admin(s) migrated")
                
                if migrated_count > 0:
                    print("\n  Note: The 'admin' table is kept for backup. You can remove it manually after verification.")
            else:
                print("\nStep 3: No 'admin' table found - skipping admin migration")
            
            # Step 4: Verify migration
            print("\n" + "="*50)
            print("MIGRATION VERIFICATION")
            print("="*50)
            
            # Count users by role
            result = conn.execute(text("SELECT role, COUNT(*) as count FROM users GROUP BY role"))
            role_counts = result.fetchall()
            
            print("\nUsers by role:")
            for role, count in role_counts:
                print(f"  - {role}: {count}")
            
            # List admin users
            result = conn.execute(text("SELECT id, username, email FROM users WHERE role = 'admin'"))
            admins = result.fetchall()
            
            if admins:
                print("\nAdmin users:")
                for admin_id, username, email in admins:
                    print(f"  - {username} (ID: {admin_id}, Email: {email})")
            
            conn.close()
            
            print("\n" + "="*50)
            print("MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*50)
            print("\nNext steps:")
            print("1. Restart your Flask application")
            print("2. Login with your admin credentials at /login")
            print("3. Admin users will be redirected to the dashboard")
            print("4. Regular users will be redirected to the homepage")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            conn.rollback()
            conn.close()
            return False


if __name__ == '__main__':
    print("="*50)
    print("ROLE-BASED AUTHENTICATION MIGRATION")
    print("="*50)
    print()
    
    success = migrate_roles()
    sys.exit(0 if success else 1)

