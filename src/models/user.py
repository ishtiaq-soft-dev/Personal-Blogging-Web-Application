from src.extensions import db, bcrypt
from flask_login import UserMixin
from datetime import datetime
from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user


# Role constants for scalability
class UserRole:
    ADMIN = "admin"
    USER = "user"
    # Future roles can be added here:
    # MODERATOR = 'moderator'
    # EDITOR = 'editor'


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(
        db.String(120), unique=True, nullable=True
    )  # Nullable for admin migration
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), nullable=False, default=UserRole.USER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    likes = db.relationship(
        "Like", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    comment_likes = db.relationship(
        "CommentLike", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN

    @property
    def is_regular_user(self):
        """Check if user has regular user role"""
        return self.role == UserRole.USER

    def has_role(self, role):
        """Check if user has a specific role"""
        return self.role == role

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


def admin_required(f):
    """
    Decorator to protect routes that require admin access.
    Must be used after @login_required.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("public.login"))
        if not current_user.is_admin:
            flash("Access denied. Admin privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


# Keep Admin model for backward compatibility during migration
# This will be deprecated and can be removed after migration
class Admin(UserMixin, db.Model):
    __tablename__ = "admin"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

