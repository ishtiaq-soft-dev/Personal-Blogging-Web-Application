from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import User, Post, Category, Tag, Comment, Like, PostMedia, UserRole
from . import admin_bp
from .forms import PostForm, CategoryForm, TagForm
from utils import allowed_file, sanitize_html, is_image_file, is_video_file
from datetime import datetime
import os


@admin_bp.before_request
def restrict_admin_routes():
    """
    Ensure only authenticated admin users can access admin routes.
    This is the primary security guard for all admin routes.
    """
    # Allow access to admin login redirect (redirects to public login)
    open_endpoints = {"admin.login", "admin.logout"}
    
    if request.endpoint and request.endpoint.startswith("admin."):
        if request.endpoint in open_endpoints:
            return  # Allow access to open endpoints
        
        # Check if user is authenticated
        if not current_user.is_authenticated:
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for("public.login", next=request.url))
        
        # Check if user has admin role
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            abort(403)


def generate_unique_slug(title: str, post_id: int | None = None) -> str:
    """Generate a unique slug for the given title."""
    from slugify import slugify

    base = slugify(title) or "post"
    slug = base
    counter = 2
    while True:
        query = Post.query.filter_by(slug=slug)
        if post_id:
            query = query.filter(Post.id != post_id)
        if not query.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Redirect to unified login page.
    The separate admin login is deprecated - all users login through /login
    """
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    # Redirect to unified public login
    flash('Please use the unified login page.', 'info')
    return redirect(url_for('public.login', next=url_for('admin.dashboard')))

@admin_bp.route('/logout')
@login_required
def logout():
    """Admin logout - redirect to public login"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.login'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    total_posts = Post.query.count()
    published_posts = Post.query.filter_by(is_published=True).count()
    draft_posts = Post.query.filter_by(is_published=False).count()
    total_comments = Comment.query.count()
    total_likes = Like.query.count()
    total_categories = Category.query.count()
    total_tags = Tag.query.count()
    
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_posts=total_posts,
                         published_posts=published_posts,
                         draft_posts=draft_posts,
                         total_comments=total_comments,
                         total_likes=total_likes,
                         total_categories=total_categories,
                         total_tags=total_tags,
                         recent_posts=recent_posts,
                         recent_comments=recent_comments)

@admin_bp.route('/posts')
@login_required
def posts():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('admin/posts.html', posts=posts)

@admin_bp.route('/posts/create', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        slug = generate_unique_slug(form.title.data)
        
        # Handle thumbnail upload (for backward compatibility)
        thumbnail_filename = None
        if form.thumbnail.data:
            file = form.thumbnail.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                thumbnail_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], thumbnail_filename)
                file.save(file_path)
        
        # Sanitize content
        sanitized_content = sanitize_html(form.content.data)
        
        post = Post(
            title=form.title.data,
            slug=slug,
            content=sanitized_content,
            thumbnail=thumbnail_filename,
            category_id=form.category.data if form.category.data else None,
            is_published=form.is_published.data
        )
        
        # Handle multiple media files
        files = request.files.getlist('media_files')
        if files and any(f.filename for f in files):
            for index, file in enumerate(files):
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{index}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    # Determine media type
                    media_type = 'image' if is_image_file(filename) else 'video'
                    
                    # Create PostMedia entry
                    post_media = PostMedia(
                        post_id=post.id,  # Will be set after commit
                        filename=unique_filename,
                        media_type=media_type,
                        order_index=index
                    )
                    post.media.append(post_media)
        
        # Add tags
        if form.tags.data:
            selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
            post.tags = selected_tags
        
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('admin.posts'))
    
    return render_template('admin/post_form.html', form=form, title='Create Post')

@admin_bp.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    form = PostForm(obj=post)
    
    if form.validate_on_submit():
        post.title = form.title.data
        post.slug = generate_unique_slug(form.title.data, post_id=post.id)
        post.content = sanitize_html(form.content.data)
        post.category_id = form.category.data if form.category.data else None
        post.is_published = form.is_published.data
        post.updated_at = datetime.utcnow()
        
        # Handle thumbnail upload (for backward compatibility)
        if form.thumbnail.data:
            file = form.thumbnail.data
            if file and allowed_file(file.filename):
                # Delete old thumbnail if exists
                if post.thumbnail:
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.thumbnail)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                post.thumbnail = f"{timestamp}_{filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.thumbnail)
                file.save(file_path)
        
        # Handle new media files (append to existing)
        files = request.files.getlist('media_files')
        if files and any(f.filename for f in files):
            existing_count = len(post.media)
            for index, file in enumerate(files):
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{existing_count + index}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    # Determine media type
                    media_type = 'image' if is_image_file(filename) else 'video'
                    
                    # Create PostMedia entry
                    post_media = PostMedia(
                        post_id=post.id,
                        filename=unique_filename,
                        media_type=media_type,
                        order_index=existing_count + index
                    )
                    post.media.append(post_media)
        
        # Update tags
        if form.tags.data:
            selected_tags = Tag.query.filter(Tag.id.in_(form.tags.data)).all()
            post.tags = selected_tags
        else:
            post.tags = []
        
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('admin.posts'))
    
    # Pre-populate form
    form.category.data = post.category_id
    form.tags.data = [tag.id for tag in post.tags]
    
    return render_template('admin/post_form.html', form=form, post=post, title='Edit Post')

@admin_bp.route('/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Delete thumbnail if exists
    if post.thumbnail:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.thumbnail)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # Delete all media files
    for media in post.media:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], media.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('admin.posts'))

@admin_bp.route('/posts/<int:post_id>/toggle', methods=['POST'])
@login_required
def toggle_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.is_published = not post.is_published
    db.session.commit()
    status = 'published' if post.is_published else 'unpublished'
    flash(f'Post {status} successfully!', 'success')
    return redirect(url_for('admin.posts'))

@admin_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data)
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully!', 'success')
        return redirect(url_for('admin.categories'))
    
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', form=form, categories=categories)

@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin.categories'))

@admin_bp.route('/tags', methods=['GET', 'POST'])
@login_required
def tags():
    form = TagForm()
    if form.validate_on_submit():
        tag = Tag(name=form.name.data)
        db.session.add(tag)
        db.session.commit()
        flash('Tag added successfully!', 'success')
        return redirect(url_for('admin.tags'))
    
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('admin/tags.html', form=form, tags=tags)

@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash('Tag deleted successfully!', 'success')
    return redirect(url_for('admin.tags'))

@admin_bp.route('/comments')
@login_required
def comments():
    page = request.args.get('page', 1, type=int)
    comments = Comment.query.order_by(Comment.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('admin/comments.html', comments=comments)

@admin_bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted successfully!', 'success')
    return redirect(url_for('admin.comments'))


# ============== Media Management API Endpoints ==============

@admin_bp.route('/api/media/<int:media_id>/delete', methods=['POST', 'DELETE'])
@login_required
def delete_media(media_id):
    """Delete a single media item from a post."""
    media = PostMedia.query.get_or_404(media_id)
    post_id = media.post_id
    
    # Delete the file from disk
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], media.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    db.session.delete(media)
    db.session.commit()
    
    # Reorder remaining media
    remaining_media = PostMedia.query.filter_by(post_id=post_id).order_by(PostMedia.order_index).all()
    for index, m in enumerate(remaining_media):
        m.order_index = index
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Media deleted successfully',
        'post_id': post_id
    })


@admin_bp.route('/api/posts/<int:post_id>/media/reorder', methods=['POST'])
@login_required
def reorder_media(post_id):
    """Reorder media items for a post."""
    post = Post.query.get_or_404(post_id)
    data = request.get_json() or {}
    
    media_order = data.get('order', [])  # List of media IDs in new order
    
    if not media_order:
        return jsonify({
            'success': False,
            'message': 'No order provided'
        }), 400
    
    for index, media_id in enumerate(media_order):
        media = PostMedia.query.filter_by(id=media_id, post_id=post_id).first()
        if media:
            media.order_index = index
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Media reordered successfully'
    })


@admin_bp.route('/api/posts/<int:post_id>/media', methods=['GET'])
@login_required
def get_post_media(post_id):
    """Get all media for a post."""
    post = Post.query.get_or_404(post_id)
    
    media_list = []
    for media in post.media:
        media_list.append({
            'id': media.id,
            'filename': media.filename,
            'media_type': media.media_type,
            'order_index': media.order_index,
            'url': f'/static/uploads/{media.filename}',
            'created_at': media.created_at.isoformat() if media.created_at else None
        })
    
    return jsonify({
        'success': True,
        'post_id': post_id,
        'media': media_list
    })


