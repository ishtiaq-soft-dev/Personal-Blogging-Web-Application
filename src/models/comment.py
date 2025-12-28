from src.extensions import db
from datetime import datetime


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
            from src.models.comment import CommentLike

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

