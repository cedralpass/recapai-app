from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, Length
import sqlalchemy as sa
from recap import db
from recap.models import User


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    phone = StringField('Phone',validators=[Length(min=10, max=10)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Submit')
    
    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == self.username.data))
            if user is not None:
                raise ValidationError('Please use a different username.')

class ArticleForm(FlaskForm):
    url_path = StringField('Let AI summarize an article for reading later', validators=[DataRequired()], render_kw={'placeholder': 'http://good.blog.com/interesting-article'})
    submit = SubmitField('Submit')