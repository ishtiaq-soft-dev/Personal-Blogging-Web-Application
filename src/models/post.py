from src.extensions import db
from datetime import datetime


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

