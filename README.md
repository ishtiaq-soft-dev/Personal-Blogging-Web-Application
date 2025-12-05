# Flask Blogging Web Application

A modern, secure blogging platform built with Flask and SQLite3. This application features an admin-controlled content management system where only administrators can create, edit, and delete posts. Public users can read posts, like them, comment, search, and share.

## Features

### Public Features (No Authentication Required)
- ✅ View latest blog posts on homepage
- ✅ Read full blog posts with SEO-friendly slugs
- ✅ Browse posts by category and tags
- ✅ Search functionality
- ✅ Like posts (IP/Session-based, prevents duplicates)
- ✅ Comment on posts (name + comment)
- ✅ Social media sharing (Facebook, Twitter, WhatsApp)
- ✅ Pagination on all lists
- ✅ Responsive Bootstrap 5 UI

### Admin Features (Authentication Required)
- ✅ Secure admin login
- ✅ Admin dashboard with statistics
- ✅ Create, edit, and delete blog posts
- ✅ Rich text editor (Quill.js) for post content
- ✅ Upload thumbnail images
- ✅ Publish/unpublish posts (draft system)
- ✅ Manage categories
- ✅ Manage tags
- ✅ View and manage comments
- ✅ View likes count
- ✅ Image upload system

## Technology Stack

- **Backend**: Python 3.11+, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- **Database**: SQLite3
- **Frontend**: Bootstrap 5, Font Awesome, Quill.js, SweetAlert2
- **Security**: Bcrypt password hashing, CSRF protection, XSS filtering

## Installation

1. **Clone or navigate to the project directory**

2. **Create and activate virtual environment** (if not already done):
```bash
python -m venv myenv
# On Windows:
myenv\Scripts\activate
# On Linux/Mac:
source myenv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure the application**:
   - Edit `config.py` to change:
     - `SECRET_KEY` (use a strong random key in production)
     - `ADMIN_USERNAME` and `ADMIN_PASSWORD` (default: admin/admin123)
     - Database path if needed

5. **Run the application**:
```bash
python app.py
```

6. **Access the application**:
   - Public blog: http://localhost:5000
   - Admin panel: http://localhost:5000/admin/login
   - Default credentials: `admin` / `admin123` (change in production!)

## Project Structure

```
Blog_Website/
├── app.py                 # Main application file
├── config.py              # Configuration settings
├── extensions.py          # Flask extensions initialization
├── models.py              # Database models
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── blueprints/
│   ├── admin/             # Admin blueprint
│   │   ├── __init__.py
│   │   ├── routes.py      # Admin routes
│   │   └── forms.py       # Admin forms
│   └── public/            # Public blueprint
│       ├── __init__.py
│       └── routes.py      # Public routes
├── templates/
│   ├── base.html          # Base template
│   ├── admin/             # Admin templates
│   └── public/            # Public templates
└── static/
    ├── css/               # Custom CSS
    ├── js/                # Custom JavaScript
    └── uploads/           # Uploaded images
```

## Database Schema

- **admin**: Admin users (id, username, password_hash)
- **posts**: Blog posts (id, title, slug, content, thumbnail, category_id, is_published, timestamps)
- **comments**: Post comments (id, post_id, name, comment, created_at)
- **likes**: Post likes (id, post_id, user_identifier, created_at)
- **categories**: Post categories (id, name)
- **tags**: Post tags (id, name)
- **post_tags**: Many-to-many relationship table

## Security Features

- ✅ Password hashing with Bcrypt
- ✅ CSRF protection on all forms
- ✅ XSS filtering on user comments
- ✅ Input validation and sanitization
- ✅ Secure file upload handling
- ✅ Admin-only authentication
- ✅ SQL injection prevention (SQLAlchemy ORM)

## Usage

### Admin Login
1. Navigate to `/admin/login`
2. Enter admin credentials
3. Access dashboard to manage content

### Creating a Post
1. Login as admin
2. Go to Posts → Create New Post
3. Fill in title, content (using rich text editor)
4. Upload thumbnail (optional)
5. Select category and tags
6. Choose publish status
7. Save post

### Managing Content
- **Categories**: Create and manage post categories
- **Tags**: Create and manage post tags
- **Comments**: View and delete comments
- **Posts**: Edit, delete, or toggle publish status

## Development

The application uses Flask blueprints for modular organization:
- `admin` blueprint: All admin-related routes
- `public` blueprint: All public-facing routes

## Production Deployment

Before deploying to production:

1. **Change SECRET_KEY** in `config.py` to a strong random key
2. **Change ADMIN_USERNAME and ADMIN_PASSWORD** in `config.py` or use environment variables
3. **Set up proper database** (consider PostgreSQL for production)
4. **Configure proper file storage** (consider cloud storage for images)
5. **Set up HTTPS** for secure connections
6. **Configure proper logging**
7. **Set up backup system** for database

## License

This project is open source and available for use.

## Support

For issues or questions, please check the code comments or Flask documentation.


