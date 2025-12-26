from flask import Flask
from config import Config
from extensions import db, bcrypt, login_manager, csrf
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Create upload directory
    upload_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    
    # Register blueprints
    from blueprints.admin import admin_bp
    from blueprints.public import public_bp
    
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(public_bp)
    
    # Context processor for global template variables
    @app.context_processor
    def inject_categories():
        from models import Category, Tag, UserRole
        from utils import time_ago, get_avatar_initials
        return dict(
            categories=Category.query.order_by(Category.name).all(),
            tags=Tag.query.order_by(Tag.name).all(),
            time_ago=time_ago,
            get_avatar_initials=get_avatar_initials,
            UserRole=UserRole  # Make UserRole available in templates
        )
    
    # User loader for Flask-Login - unified User model with roles
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Create tables and run migrations
    with app.app_context():
        db.create_all()
        
        # Run database migrations
        try:
            from sqlalchemy import inspect, text
            conn = db.engine.connect()
            
            # Check if parent_comment_id column exists in comments table
            inspector = inspect(db.engine)
            comments_columns = [col['name'] for col in inspector.get_columns('comments')]
            
            if 'parent_comment_id' not in comments_columns:
                print("Migrating: Adding parent_comment_id column to comments table...")
                conn.execute(text("ALTER TABLE comments ADD COLUMN parent_comment_id INTEGER"))
                conn.commit()
                print("Migration completed: parent_comment_id column added")
            
            # Check if comment_likes table exists
            tables = inspector.get_table_names()
            if 'comment_likes' not in tables:
                print("Migrating: Creating comment_likes table...")
                conn.execute(text("""
                    CREATE TABLE comment_likes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        comment_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY (comment_id) REFERENCES comments(id),
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        UNIQUE(comment_id, user_id)
                    )
                """))
                conn.commit()
                print("Migration completed: comment_likes table created")
            
            # Check if users table exists
            if 'users' not in tables:
                print("Migrating: Creating users table...")
                conn.execute(text("""
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username VARCHAR(80) NOT NULL UNIQUE,
                        email VARCHAR(120) UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        full_name VARCHAR(100),
                        role VARCHAR(20) DEFAULT 'user' NOT NULL,
                        created_at DATETIME NOT NULL
                    )
                """))
                conn.commit()
                print("Migration completed: users table created")
            
            # Check if role column exists in users table and add if not
            users_columns = [col['name'] for col in inspector.get_columns('users')]
            if 'role' not in users_columns:
                print("Migrating: Adding role column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL"))
                conn.commit()
                print("Migration completed: role column added to users")
            
            # Check if user_id columns exist and add them if needed
            comments_columns = [col['name'] for col in inspector.get_columns('comments')]
            if 'user_id' not in comments_columns:
                print("Migrating: Adding user_id to comments table...")
                conn.execute(text("ALTER TABLE comments ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                conn.commit()
                print("Migration completed: user_id added to comments")
            
            likes_columns = [col['name'] for col in inspector.get_columns('likes')]
            if 'user_id' not in likes_columns:
                print("Migrating: Adding user_id to likes table...")
                conn.execute(text("ALTER TABLE likes ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                conn.commit()
                print("Migration completed: user_id added to likes")
            
            conn.close()
        except Exception as e:
            print(f"Migration check completed (or skipped): {e}")
        
        # Create default admin if not exists (using unified User model with role)
        from models import User, UserRole
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        if not admin:
            default_admin = User(
                username=app.config['ADMIN_USERNAME'],
                email=f"{app.config['ADMIN_USERNAME']}@admin.local",
                password_hash=bcrypt.generate_password_hash(app.config['ADMIN_PASSWORD']).decode('utf-8'),
                role=UserRole.ADMIN
            )
            db.session.add(default_admin)
            db.session.commit()
            print(f"Default admin created: {app.config['ADMIN_USERNAME']}")
    
    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

