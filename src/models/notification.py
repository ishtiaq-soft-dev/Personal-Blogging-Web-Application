from src.extensions import db
from datetime import datetime


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

