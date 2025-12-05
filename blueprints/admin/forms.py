from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SelectMultipleField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from models import Category, Tag

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    thumbnail = FileField('Thumbnail Image', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')])
    category = SelectField('Category', coerce=int, validators=[Optional()])
    tags = SelectMultipleField('Tags', coerce=int, validators=[Optional()])
    is_published = BooleanField('Publish', default=False)
    submit = SubmitField('Save Post')
    
    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.category.choices = [(0, 'No Category')] + [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
        self.tags.choices = [(t.id, t.name) for t in Tag.query.order_by(Tag.name).all()]

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Add Category')
    
    def validate_name(self, name):
        category = Category.query.filter_by(name=name.data).first()
        if category:
            raise ValidationError('Category already exists.')

class TagForm(FlaskForm):
    name = StringField('Tag Name', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Add Tag')
    
    def validate_name(self, name):
        tag = Tag.query.filter_by(name=name.data).first()
        if tag:
            raise ValidationError('Tag already exists.')


