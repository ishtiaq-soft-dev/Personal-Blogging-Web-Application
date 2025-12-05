from slugify import slugify
from bleach import clean, linkify
from flask import request, session
import uuid

def generate_slug(title):
    """Generate a unique slug from title"""
    base_slug = slugify(title)
    return base_slug

def allowed_file(filename):
    """Check if file extension is allowed"""
    from config import Config
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def sanitize_html(content):
    """Sanitize HTML content to prevent XSS attacks"""
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                   'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre']
    allowed_attributes = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title', 'width', 'height']
    }
    
    # Clean HTML
    cleaned = clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    # Convert URLs to links
    cleaned = linkify(cleaned)
    return cleaned

def get_user_identifier():
    """Get unique identifier for user (IP + session)"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    # Combine session ID with IP for better uniqueness
    ip = request.remote_addr or 'unknown'
    return f"{session['user_id']}_{ip}"


