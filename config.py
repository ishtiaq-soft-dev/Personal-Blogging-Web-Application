import os
from pathlib import Path

basedir = Path(__file__).parent.absolute()

from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{basedir}/blog.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    
    # Upload settings
    UPLOAD_FOLDER = basedir / 'static' / 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size (for videos)
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov', 'avi'}
    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
    
    # Pagination
    POSTS_PER_PAGE = 6
    
    # Admin settings
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'  # Change in production!


