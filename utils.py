from slugify import slugify
from bleach import clean, linkify
from flask import request, session
from datetime import datetime, timedelta
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

def is_image_file(filename):
    """Check if file is an image"""
    from config import Config
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS

def is_video_file(filename):
    """Check if file is a video"""
    from config import Config
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_VIDEO_EXTENSIONS

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

def time_ago(dt):
    """Convert datetime to Facebook-style 'time ago' format"""
    if dt is None:
        return "just now"
    
    # Handle timezone-aware and naive datetimes
    now = datetime.utcnow()
    if dt.tzinfo:
        # Convert timezone-aware to UTC naive
        dt = dt.replace(tzinfo=None) - (dt.utcoffset() or timedelta(0))
    
    diff = now - dt
    
    seconds = diff.total_seconds()
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24
    weeks = days / 7
    months = days / 30
    years = days / 365
    
    if seconds < 60:
        return "just now"
    elif minutes < 60:
        m = int(minutes)
        return f"{m}m" if m == 1 else f"{m}m"
    elif hours < 24:
        h = int(hours)
        return f"{h}h" if h == 1 else f"{h}h"
    elif days < 7:
        d = int(days)
        return f"{d}d" if d == 1 else f"{d}d"
    elif weeks < 4:
        w = int(weeks)
        return f"{w}w" if w == 1 else f"{w}w"
    elif months < 12:
        m = int(months)
        return f"{m}mo" if m == 1 else f"{m}mo"
    else:
        y = int(years)
        return f"{y}y" if y == 1 else f"{y}y"

def get_avatar_initials(name):
    """Get initials from name for avatar"""
    if not name:
        return "?"
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[0].upper() if name else "?"


