from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length


class CommentForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    comment = TextAreaField("Comment", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Post Comment")

