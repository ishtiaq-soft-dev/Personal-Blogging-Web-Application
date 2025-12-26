"""
Migration script to migrate existing thumbnail data to PostMedia table.
This ensures backward compatibility while transitioning to multi-media support.

Run this script once after deploying the new code:
    python migrate_media.py
"""

import os
import sys

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import Post, PostMedia

# Create the app
app = create_app()


def migrate_thumbnails_to_media():
    """Migrate existing thumbnail field data to PostMedia table."""
    with app.app_context():
        # Get all posts with thumbnails that don't already have media
        posts_with_thumbnails = Post.query.filter(
            Post.thumbnail.isnot(None),
            Post.thumbnail != ''
        ).all()
        
        migrated_count = 0
        skipped_count = 0
        
        for post in posts_with_thumbnails:
            # Check if this post already has media entries
            existing_media = PostMedia.query.filter_by(post_id=post.id).first()
            
            if existing_media:
                print(f"Skipping post {post.id} '{post.title}' - already has media entries")
                skipped_count += 1
                continue
            
            # Determine media type from filename
            filename = post.thumbnail
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            video_extensions = {'mp4', 'webm', 'ogg', 'mov', 'avi'}
            
            if ext in image_extensions:
                media_type = 'image'
            elif ext in video_extensions:
                media_type = 'video'
            else:
                print(f"Unknown file type for post {post.id}: {filename}")
                continue
            
            # Create PostMedia entry
            post_media = PostMedia(
                post_id=post.id,
                filename=filename,
                media_type=media_type,
                order_index=0
            )
            db.session.add(post_media)
            migrated_count += 1
            print(f"Migrated post {post.id} '{post.title}' - thumbnail: {filename}")
        
        db.session.commit()
        
        print(f"\n=== Migration Complete ===")
        print(f"Migrated: {migrated_count} posts")
        print(f"Skipped: {skipped_count} posts (already had media)")
        print(f"Total posts processed: {migrated_count + skipped_count}")


def create_post_media_table():
    """Create PostMedia table if it doesn't exist."""
    with app.app_context():
        # Create all tables (will skip existing ones)
        db.create_all()
        print("Database tables created/verified.")


if __name__ == '__main__':
    print("=== Starting Media Migration ===\n")
    
    # Step 1: Ensure table exists
    create_post_media_table()
    
    # Step 2: Migrate existing thumbnails
    migrate_thumbnails_to_media()
    
    print("\n=== Migration process completed! ===")

