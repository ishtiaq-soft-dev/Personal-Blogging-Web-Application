from flask import render_template, request, jsonify, flash, session, redirect, url_for
from extensions import db
from models import Post, Category, Tag, Comment, Like
from utils import sanitize_html, get_user_identifier
from datetime import datetime
from sqlalchemy import or_, func
from .forms import CommentForm
from . import public_bp


@public_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    category_id = request.args.get("category", type=int)
    tag_id = request.args.get("tag", type=int)
    search = request.args.get("search", "", type=str)

    query = Post.query.filter_by(is_published=True)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if tag_id:
        query = query.filter(Post.tags.any(Tag.id == tag_id))

    if search:
        query = query.filter(
            or_(Post.title.ilike(f"%{search}%"), Post.content.ilike(f"%{search}%"))
        )

    posts = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=6, error_out=False
    )

    categories = Category.query.all()
    tags = Tag.query.all()

    return render_template(
        "public/index.html",
        posts=posts,
        categories=categories,
        tags=tags,
        current_category=category_id,
        current_tag=tag_id,
        search_query=search,
    )


@public_bp.route("/post/<slug>")
def post_detail(slug):
    post = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    form = CommentForm()

    # Get related posts (same category)
    related_posts = (
        Post.query.filter(
            Post.category_id == post.category_id,
            Post.id != post.id,
            Post.is_published == True,
        )
        .limit(3)
        .all()
    )

    return render_template(
        "public/post_detail.html",
        post=post,
        related_posts=related_posts,
        form=form,
    )


@public_bp.route("/post/<int:post_id>/like", methods=["POST"])
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    user_id = get_user_identifier()

    # Check if already liked
    existing_like = Like.query.filter_by(
        post_id=post_id, user_identifier=user_id
    ).first()

    if existing_like:
        return jsonify(
            {"success": False, "message": "You have already liked this post."}
        )

    like = Like(post_id=post_id, user_identifier=user_id)
    db.session.add(like)
    db.session.commit()

    # Refresh post to get updated likes count
    db.session.refresh(post)
    likes_count = Like.query.filter_by(post_id=post_id).count()

    return jsonify(
        {
            "success": True,
            "message": "Post liked successfully!",
            "likes_count": likes_count,
        }
    )


@public_bp.route("/post/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    form = CommentForm()

    if not form.validate_on_submit():
        # Show the first error to the user
        for field_errors in form.errors.values():
            if field_errors:
                flash(field_errors[0], "danger")
                break
        return redirect(url_for("public.post_detail", slug=post.slug))

    name = form.name.data.strip()
    comment_text = form.comment.data.strip()

    if not name or not comment_text:
        flash("Name and comment are required.", "danger")
        return redirect(url_for("public.post_detail", slug=post.slug))

    if len(name) > 100:
        flash("Name is too long.", "danger")
        return redirect(url_for("public.post_detail", slug=post.slug))

    if len(comment_text) > 2000:
        flash("Comment is too long.", "danger")
        return redirect(url_for("public.post_detail", slug=post.slug))

    # Sanitize input
    sanitized_name = sanitize_html(name)
    sanitized_comment = sanitize_html(comment_text)

    comment = Comment(post_id=post_id, name=sanitized_name, comment=sanitized_comment)

    db.session.add(comment)
    db.session.commit()

    flash("Comment added successfully!", "success")
    return redirect(url_for("public.post_detail", slug=post.slug))


@public_bp.route("/category/<int:category_id>")
def category_posts(category_id):
    category = Category.query.get_or_404(category_id)
    page = request.args.get("page", 1, type=int)

    posts = (
        Post.query.filter_by(category_id=category_id, is_published=True)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=6, error_out=False)
    )

    return render_template("public/category.html", category=category, posts=posts)


@public_bp.route("/tag/<int:tag_id>")
def tag_posts(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    page = request.args.get("page", 1, type=int)

    posts = (
        Post.query.filter(Post.tags.any(Tag.id == tag_id), Post.is_published == True)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=6, error_out=False)
    )

    return render_template("public/tag.html", tag=tag, posts=posts)
