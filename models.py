from extensions import db, bcrypt
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func
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


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship(
        "Post", backref="category", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship(
        "Post", secondary="post_tags", backref="tags", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Tag {self.name}>"


post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("posts.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    thumbnail = db.Column(
        db.String(255), nullable=True
    )  # Keep for backward compatibility
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    comments = db.relationship(
        "Comment",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="Comment.post_id",
        order_by="Comment.created_at.desc()",
    )
    likes = db.relationship(
        "Like", backref="post", lazy=True, cascade="all, delete-orphan"
    )
    media = db.relationship(
        "PostMedia",
        backref="post",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="PostMedia.order_index",
    )

    def __repr__(self):
        return f"<Post {self.title}>"

    @property
    def likes_count(self):
        return len(self.likes)

    @property
    def comments_count(self):
        return len(self.comments)

    @property
    def images(self):
        """Get all image media"""
        return [m for m in self.media if m.media_type == "image"]

    @property
    def videos(self):
        """Get all video media"""
        return [m for m in self.media if m.media_type == "video"]

    @property
    def first_image(self):
        """Get first image for thumbnail/display"""
        images = self.images
        return images[0] if images else None


class PostMedia(db.Model):
    __tablename__ = "post_media"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # 'image' or 'video'
    order_index = db.Column(
        db.Integer, default=0, nullable=False
    )  # For ordering multiple media
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PostMedia {self.filename}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    parent_comment_id = db.Column(
        db.Integer, db.ForeignKey("comments.id"), nullable=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )  # Nullable for migration
    name = db.Column(db.String(100), nullable=True)  # Keep for backward compatibility
    comment = db.Column(db.Text, nullable=False)  # Content of the comment
    image = db.Column(db.String(255), nullable=True)  # Optional image attachment
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Self-referential relationship for nested comments (with cascade delete)
    parent = db.relationship(
        "Comment",
        remote_side=[id],
        backref=db.backref("replies", lazy="dynamic", cascade="all, delete-orphan"),
        lazy="joined",
    )
    comment_likes = db.relationship(
        "CommentLike", backref="comment", lazy="select", cascade="all, delete-orphan"
    )

    # Index for faster queries
    __table_args__ = (
        db.Index("idx_comment_post_parent", "post_id", "parent_comment_id"),
    )

    @property
    def content(self):
        """Alias for comment field for API compatibility"""
        return self.comment

    @content.setter
    def content(self, value):
        """Setter for content alias"""
        self.comment = value

    @property
    def display_name(self):
        """Get display name from user or fallback to name field"""
        if self.user:
            return self.user.full_name or self.user.username
        return self.name or "Anonymous"

    def __repr__(self):
        return f"<Comment {self.id}>"

    @property
    def likes_count(self):
        return len(self.comment_likes)

    @property
    def replies_count(self):
        """Get count of direct replies"""
        return (
            self.replies.count()
            if hasattr(self.replies, "count")
            else len(list(self.replies))
        )

    def get_replies(self, limit=None):
        """Get direct replies to this comment with optional limit"""
        query = Comment.query.filter_by(parent_comment_id=self.id).order_by(
            Comment.created_at.asc()
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def to_dict(
        self, include_replies=True, max_depth=10, current_depth=0, user_liked_ids=None
    ):
        """Convert comment to dictionary for JSON API"""
        if user_liked_ids is None:
            user_liked_ids = set()

        data = {
            "id": self.id,
            "post_id": self.post_id,
            "parent_comment_id": self.parent_comment_id,
            "user_id": self.user_id,
            "content": self.comment,
            "image": self.image,
            "author": self.display_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "likes_count": self.likes_count,
            "replies_count": self.replies_count,
            "is_liked": self.id in user_liked_ids,
            "depth": current_depth,
        }

        if include_replies and current_depth < max_depth:
            replies = self.get_replies()
            data["replies"] = [
                reply.to_dict(
                    include_replies=True,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    user_liked_ids=user_liked_ids,
                )
                for reply in replies
            ]
        else:
            data["replies"] = []
            data["has_more_replies"] = self.replies_count > 0

        return data

    @staticmethod
    def get_comment_tree(post_id, user_id=None, limit_top_level=None, max_depth=10):
        """
        Get all comments for a post as a tree structure.
        Optimized to minimize database queries.
        """
        # Get user's liked comment IDs
        user_liked_ids = set()
        if user_id:
            from models import CommentLike

            user_liked_ids = {
                like.comment_id
                for like in CommentLike.query.filter_by(user_id=user_id).all()
            }

        # Get top-level comments
        query = Comment.query.filter_by(
            post_id=post_id, parent_comment_id=None
        ).order_by(Comment.created_at.desc())

        if limit_top_level:
            query = query.limit(limit_top_level)

        top_level_comments = query.all()

        return [
            comment.to_dict(
                include_replies=True, max_depth=max_depth, user_liked_ids=user_liked_ids
            )
            for comment in top_level_comments
        ]


class Like(db.Model):
    __tablename__ = "likes"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("post_id", "user_id", name="unique_like"),)

    def __repr__(self):
        return f"<Like {self.id}>"


class CommentLike(db.Model):
    __tablename__ = "comment_likes"

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("comment_id", "user_id", name="unique_comment_like"),
    )

    def __repr__(self):
        return f"<CommentLike {self.id}>"


class NotificationType:
    """Notification type constants"""

    REPLY = "reply"
    LIKE = "like"
    MENTION = "mention"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # reply, like, mention
    message = db.Column(db.String(500), nullable=False)

    # Related entities
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)

    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("notifications", lazy="dynamic"),
    )
    from_user = db.relationship("User", foreign_keys=[from_user_id])
    post = db.relationship("Post", backref=db.backref("notifications", lazy="dynamic"))
    comment = db.relationship(
        "Comment", backref=db.backref("notifications", lazy="dynamic")
    )

    def __repr__(self):
        return f"<Notification {self.id} - {self.type}>"

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "message": self.message,
            "from_user": self.from_user.username if self.from_user else None,
            "from_user_name": (
                self.from_user.full_name or self.from_user.username
                if self.from_user
                else None
            ),
            "post_id": self.post_id,
            "post_slug": self.post.slug if self.post else None,
            "post_title": self.post.title if self.post else None,
            "comment_id": self.comment_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def create_reply_notification(comment, parent_comment):
        """Create a notification when someone replies to a comment"""
        # Don't notify if user is replying to their own comment
        if parent_comment.user_id == comment.user_id:
            return None

        # Don't notify if parent comment has no user
        if not parent_comment.user_id:
            return None

        from_user = comment.user
        message = f"{from_user.full_name or from_user.username} replied to your comment"

        notification = Notification(
            user_id=parent_comment.user_id,
            type=NotificationType.REPLY,
            message=message,
            from_user_id=comment.user_id,
            post_id=comment.post_id,
            comment_id=comment.id,
        )

        db.session.add(notification)
        return notification

    @staticmethod
    def get_unread_count(user_id):
        """Get count of unread notifications for a user"""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def get_notifications(user_id, limit=20, include_read=True):
        """Get notifications for a user"""
        query = Notification.query.filter_by(user_id=user_id)
        if not include_read:
            query = query.filter_by(is_read=False)
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
