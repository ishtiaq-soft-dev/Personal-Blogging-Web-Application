from flask import render_template, request, jsonify, flash, session, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import Post, Category, Tag, Comment, Like, CommentLike, User, UserRole
from utils import sanitize_html, get_user_identifier
from datetime import datetime
from sqlalchemy import or_, func
from .forms import CommentForm, LoginForm, SignupForm
from . import public_bp
from werkzeug.utils import secure_filename
import os
import uuid


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

    # Get top-level comments with eager loading for user relationship
    # This reduces N+1 queries when displaying comments
    top_level_comments = (
        Comment.query
        .filter_by(post_id=post.id, parent_comment_id=None)
        .options(
            db.joinedload(Comment.user),
            db.joinedload(Comment.comment_likes)
        )
        .order_by(Comment.created_at.desc())
        .all()
    )
    
    # Check if current user has liked the post
    is_post_liked = False
    user_comment_likes = set()
    
    if current_user.is_authenticated:
        # Batch query for post like check
        is_post_liked = Like.query.filter_by(
            post_id=post.id, 
            user_id=current_user.id
        ).first() is not None
        
        # Get all comment likes for this user in one query (for all comments in post)
        user_comment_likes = {
            like.comment_id for like in 
            CommentLike.query
            .join(Comment)
            .filter(Comment.post_id == post.id, CommentLike.user_id == current_user.id)
            .all()
        }

    # Get related posts (same category)
    related_posts = []
    if post.category_id:
        related_posts = (
            Post.query.filter(
                Post.category_id == post.category_id,
                Post.id != post.id,
                Post.is_published == True,
            )
            .limit(3)
            .all()
        )
    
    # Calculate total comments count for display
    total_comments = Comment.query.filter_by(post_id=post.id).count()

    return render_template(
        "public/post_detail.html",
        post=post,
        related_posts=related_posts,
        form=form,
        top_level_comments=top_level_comments,
        user_comment_likes=user_comment_likes,
        is_post_liked=is_post_liked,
        total_comments=total_comments,
    )


@public_bp.route("/post/<int:post_id>/like", methods=["POST"])
def like_post(post_id):
    # Check if user is authenticated
    if not current_user.is_authenticated:
        post = Post.query.get(post_id)
        return jsonify({
            "success": False,
            "message": "Please login to like posts.",
            "redirect": url_for('public.login', next=request.referrer or url_for('public.post_detail', slug=post.slug if post else ''))
        }), 401
    
    post = Post.query.get_or_404(post_id)
    user_id = current_user.id

    # Check if already liked
    existing_like = Like.query.filter_by(
        post_id=post_id, user_id=user_id
    ).first()

    if existing_like:
        # Unlike - remove the like
        db.session.delete(existing_like)
        db.session.commit()
        likes_count = Like.query.filter_by(post_id=post_id).count()
        return jsonify(
            {
                "success": True,
                "message": "Post unliked",
                "likes_count": likes_count,
                "liked": False,
            }
        )

    like = Like(post_id=post_id, user_id=user_id)
    db.session.add(like)
    db.session.commit()

    likes_count = Like.query.filter_by(post_id=post_id).count()

    return jsonify(
        {
            "success": True,
            "message": "Post liked successfully!",
            "likes_count": likes_count,
            "liked": True,
        }
    )


@public_bp.route("/post/<int:post_id>/comment", methods=["POST"])
def add_comment(post_id):
    # Check if user is authenticated
    if not current_user.is_authenticated:
        flash("Please login to comment.", "warning")
        return redirect(url_for('public.login', next=request.url))
    
    post = Post.query.get_or_404(post_id)
    form = CommentForm()

    if not form.validate_on_submit():
        # Show the first error to the user
        for field_errors in form.errors.values():
            if field_errors:
                flash(field_errors[0], "danger")
                break
        return redirect(url_for("public.post_detail", slug=post.slug))

    comment_text = form.comment.data.strip()
    
    # Get parent_comment_id directly from request.form
    parent_comment_id = request.form.get('parent_comment_id', '').strip()

    if not comment_text:
        flash("Comment is required.", "danger")
        return redirect(url_for("public.post_detail", slug=post.slug))

    if len(comment_text) > 2000:
        flash("Comment is too long.", "danger")
        return redirect(url_for("public.post_detail", slug=post.slug))

    # Validate parent_comment_id if provided and not empty
    if parent_comment_id and parent_comment_id != '':
        try:
            parent_comment_id = int(parent_comment_id)
            parent_comment = Comment.query.filter_by(
                id=parent_comment_id, 
                post_id=post_id
            ).first()
            if not parent_comment:
                flash("Invalid parent comment.", "danger")
                return redirect(url_for("public.post_detail", slug=post.slug))
        except (ValueError, TypeError):
            parent_comment_id = None
    else:
        parent_comment_id = None

    # Sanitize input
    sanitized_comment = sanitize_html(comment_text)

    comment = Comment(
        post_id=post_id, 
        user_id=current_user.id,
        comment=sanitized_comment,
        parent_comment_id=parent_comment_id
    )

    db.session.add(comment)
    db.session.commit()

    flash("Comment added successfully!", "success")
    return redirect(url_for("public.post_detail", slug=post.slug))


@public_bp.route("/comment/<int:comment_id>/like", methods=["POST"])
def like_comment(comment_id):
    # Check if user is authenticated
    if not current_user.is_authenticated:
        return jsonify({
            "success": False,
            "message": "Please login to like comments.",
            "redirect": url_for('public.login', next=request.referrer)
        }), 401
    
    comment = Comment.query.get_or_404(comment_id)
    user_id = current_user.id

    # Check if already liked
    existing_like = CommentLike.query.filter_by(
        comment_id=comment_id, user_id=user_id
    ).first()

    if existing_like:
        # Unlike - remove the like
        db.session.delete(existing_like)
        db.session.commit()
        likes_count = CommentLike.query.filter_by(comment_id=comment_id).count()
        return jsonify(
            {
                "success": True,
                "message": "Comment unliked",
                "likes_count": likes_count,
                "liked": False,
            }
        )

    like = CommentLike(comment_id=comment_id, user_id=user_id)
    db.session.add(like)
    db.session.commit()

    likes_count = CommentLike.query.filter_by(comment_id=comment_id).count()

    return jsonify(
        {
            "success": True,
            "message": "Comment liked successfully!",
            "likes_count": likes_count,
            "liked": True,
        }
    )


# ============== Comment API Endpoints ==============

@public_bp.route("/api/post/<int:post_id>/comments", methods=["GET"])
def get_comments_tree(post_id):
    """
    API endpoint to get all comments for a post as a tree structure.
    Query params:
    - limit: Number of top-level comments to return (default: all)
    - max_depth: Maximum nesting depth (default: 10)
    """
    post = Post.query.get_or_404(post_id)
    
    limit = request.args.get('limit', type=int)
    max_depth = request.args.get('max_depth', 10, type=int)
    
    # Get user ID if authenticated
    user_id = None
    if current_user.is_authenticated:
        user_id = current_user.id
    
    comments_tree = Comment.get_comment_tree(
        post_id=post.id,
        user_id=user_id,
        limit_top_level=limit,
        max_depth=max_depth
    )
    
    # Get total comment count
    total_comments = Comment.query.filter_by(post_id=post.id).count()
    top_level_count = Comment.query.filter_by(post_id=post.id, parent_comment_id=None).count()
    
    return jsonify({
        "success": True,
        "post_id": post.id,
        "total_comments": total_comments,
        "top_level_count": top_level_count,
        "comments": comments_tree
    })


def allowed_image_file(filename):
    """Check if file is an allowed image type"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_comment_image(file):
    """Save uploaded image and return filename"""
    if file and file.filename and allowed_image_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"comment_{uuid.uuid4().hex[:12]}.{ext}"
        
        # Get upload folder from config
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, filename)
        
        # Save file
        file.save(filepath)
        return filename
    return None


@public_bp.route("/api/post/<int:post_id>/comments", methods=["POST"])
def create_comment_api(post_id):
    """
    API endpoint to create a comment via AJAX.
    Supports both JSON and multipart form data (for image uploads).
    
    JSON body / Form data:
    - content: Comment text (required)
    - parent_comment_id: Parent comment ID for replies (optional)
    - image: Image file (optional, multipart only)
    """
    # Check authentication
    if not current_user.is_authenticated:
        return jsonify({
            "success": False,
            "message": "Please login to comment.",
            "redirect": url_for('public.login')
        }), 401
    
    post = Post.query.get_or_404(post_id)
    
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        parent_comment_id = data.get('parent_comment_id')
        image_filename = None
    else:
        content = request.form.get('content', '').strip()
        parent_comment_id = request.form.get('parent_comment_id')
        
        # Handle image upload
        image_filename = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename:
                image_filename = save_comment_image(image_file)
    
    # Validate content (allow empty content if image is provided)
    if not content and not image_filename:
        return jsonify({
            "success": False,
            "message": "Comment content or image is required."
        }), 400
    
    if len(content) > 2000:
        return jsonify({
            "success": False,
            "message": "Comment is too long (max 2000 characters)."
        }), 400
    
    # Validate parent_comment_id if provided
    if parent_comment_id:
        try:
            parent_comment_id = int(parent_comment_id)
            parent_comment = Comment.query.filter_by(
                id=parent_comment_id, 
                post_id=post_id
            ).first()
            if not parent_comment:
                return jsonify({
                    "success": False,
                    "message": "Invalid parent comment."
                }), 400
        except (ValueError, TypeError):
            parent_comment_id = None
    
    # Sanitize and create comment
    sanitized_content = sanitize_html(content) if content else ""
    
    comment = Comment(
        post_id=post_id,
        user_id=current_user.id,
        comment=sanitized_content,
        parent_comment_id=parent_comment_id,
        image=image_filename
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Get user's liked comments for response
    user_liked_ids = {
        like.comment_id for like in 
        CommentLike.query.filter_by(user_id=current_user.id).all()
    }
    
    return jsonify({
        "success": True,
        "message": "Comment added successfully!",
        "comment": comment.to_dict(include_replies=False, user_liked_ids=user_liked_ids)
    }), 201


@public_bp.route("/api/comment/<int:comment_id>", methods=["PUT"])
def edit_comment_api(comment_id):
    """
    API endpoint to edit a comment.
    Only the comment owner can edit their comment.
    JSON body:
    - content: New comment text (required)
    """
    # Check authentication
    if not current_user.is_authenticated:
        return jsonify({
            "success": False,
            "message": "Please login to edit comments.",
            "redirect": url_for('public.login')
        }), 401
    
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user owns this comment
    if comment.user_id != current_user.id:
        return jsonify({
            "success": False,
            "message": "You can only edit your own comments."
        }), 403
    
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    
    # Validate content
    if not content:
        return jsonify({
            "success": False,
            "message": "Comment content is required."
        }), 400
    
    if len(content) > 2000:
        return jsonify({
            "success": False,
            "message": "Comment is too long (max 2000 characters)."
        }), 400
    
    # Sanitize and update comment
    sanitized_content = sanitize_html(content)
    comment.comment = sanitized_content
    
    db.session.commit()
    
    # Get user's liked comments for response
    user_liked_ids = {
        like.comment_id for like in 
        CommentLike.query.filter_by(user_id=current_user.id).all()
    }
    
    return jsonify({
        "success": True,
        "message": "Comment updated successfully!",
        "comment": comment.to_dict(include_replies=False, user_liked_ids=user_liked_ids)
    })


@public_bp.route("/api/comment/<int:comment_id>", methods=["DELETE"])
def delete_comment_api(comment_id):
    """
    API endpoint to delete a comment.
    Only the comment owner can delete their comment.
    Also deletes all replies to this comment.
    """
    # Check authentication
    if not current_user.is_authenticated:
        return jsonify({
            "success": False,
            "message": "Please login to delete comments.",
            "redirect": url_for('public.login')
        }), 401
    
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user owns this comment
    if comment.user_id != current_user.id:
        return jsonify({
            "success": False,
            "message": "You can only delete your own comments."
        }), 403
    
    # Count how many comments will be deleted (including replies)
    def count_replies(comment):
        count = 1  # Count self
        for reply in comment.get_replies():
            count += count_replies(reply)
        return count
    
    deleted_count = count_replies(comment)
    
    # Delete the comment (cascade will delete replies and likes)
    db.session.delete(comment)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Comment deleted successfully!",
        "deleted_count": deleted_count
    })


@public_bp.route("/api/comment/<int:comment_id>/replies", methods=["GET"])
def get_comment_replies(comment_id):
    """
    API endpoint to get replies for a specific comment.
    Query params:
    - limit: Number of replies to return (default: all)
    - offset: Number of replies to skip (default: 0)
    - max_depth: Maximum nesting depth for nested replies (default: 5)
    """
    comment = Comment.query.get_or_404(comment_id)
    
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)
    max_depth = request.args.get('max_depth', 5, type=int)
    
    # Get user ID if authenticated
    user_id = None
    user_liked_ids = set()
    if current_user.is_authenticated:
        user_id = current_user.id
        user_liked_ids = {
            like.comment_id for like in 
            CommentLike.query.filter_by(user_id=user_id).all()
        }
    
    # Get replies with pagination
    query = Comment.query.filter_by(
        parent_comment_id=comment_id
    ).order_by(Comment.created_at.asc())
    
    total_replies = query.count()
    
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    
    replies = query.all()
    
    return jsonify({
        "success": True,
        "comment_id": comment_id,
        "total_replies": total_replies,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + len(replies)) < total_replies if limit else False,
        "replies": [
            reply.to_dict(
                include_replies=True,
                max_depth=max_depth,
                user_liked_ids=user_liked_ids
            ) for reply in replies
        ]
    })


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


@public_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Unified login for all users (admin and regular users).
    Redirects based on role after successful authentication.
    """
    if current_user.is_authenticated:
        # Redirect based on role
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('public.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Check user credentials (works for both admin and regular users)
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            # Set session as permanent
            session.permanent = True
            # Login the user
            login_user(user, remember=form.remember_me.data)
            
            # Set user_type in session for template checks
            session['user_type'] = 'admin' if user.is_admin else 'user'
            
            # Handle next parameter for redirects
            next_page = request.args.get('next')
            
            # Role-based redirect after successful login
            if user.is_admin:
                flash('Welcome back, Admin!', 'success')
                if next_page and next_page.startswith('/admin'):
                    return redirect(next_page)
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Welcome back!', 'success')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('public.index'))
        
        flash('Invalid username or password.', 'danger')
    
    return render_template('public/login.html', form=form)


@public_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """
    User registration - creates regular users only.
    Admin users must be created via migration or database.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('public.index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=UserRole.USER  # Explicitly set role as regular user
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        # Set session as permanent
        session.permanent = True
        # Login the user
        login_user(user, remember=True)
        # Set user_type in session for template checks
        session['user_type'] = 'user'
        
        flash('Account created successfully! Welcome!', 'success')
        return redirect(url_for('public.index'))
    
    return render_template('public/signup.html', form=form)


@public_bp.route("/logout")
@login_required
def logout():
    """Logout for all users (admin and regular)."""
    # Clear user_type from session
    session.pop('user_type', None)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))
