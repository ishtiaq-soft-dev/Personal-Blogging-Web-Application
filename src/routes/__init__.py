# Routes package - exports all blueprints
from .admin import admin_bp
from .public import public_bp

__all__ = ['admin_bp', 'public_bp']

