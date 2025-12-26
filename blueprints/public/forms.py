from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, HiddenField, PasswordField, EmailField
from wtforms.validators import DataRequired, Length, Optional, Email, EqualTo, ValidationError
from models import User


class CommentForm(FlaskForm):
    name = StringField("Name", validators=[Optional(), Length(max=100)])
    comment = TextAreaField("Comment", validators=[DataRequired(), Length(max=2000)])
    parent_comment_id = HiddenField("Parent Comment ID", validators=[Optional()])
    submit = SubmitField("Post Comment")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")
    remember_me = HiddenField("Remember Me", default=False)


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    full_name = StringField("Full Name", validators=[Optional(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    password_confirm = PasswordField("Confirm Password", validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField("Sign Up")
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email or login.')
