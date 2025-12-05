from flask import Flask
from config import Config
from extensions import db, bcrypt, login_manager
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
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
        from models import Category, Tag
        return dict(
            categories=Category.query.order_by(Category.name).all(),
            tags=Tag.query.order_by(Tag.name).all()
        )
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import Admin
        return Admin.query.get(int(user_id))
    
    # Create tables
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        from models import Admin
        admin = Admin.query.first()
        if not admin:
            default_admin = Admin(
                username=app.config['ADMIN_USERNAME'],
                password_hash=bcrypt.generate_password_hash(app.config['ADMIN_PASSWORD']).decode('utf-8')
            )
            db.session.add(default_admin)
            db.session.commit()
            print(f"Default admin created: {app.config['ADMIN_USERNAME']}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

