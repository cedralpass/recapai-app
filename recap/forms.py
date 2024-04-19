from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, Length
import sqlalchemy as sa
from recap import db
from recap.models import User


class ArticleForm(FlaskForm):
    url_path = StringField('Let AI summarize an article for reading later', validators=[DataRequired()], render_kw={'placeholder': 'http://good.blog.com/interesting-article'})
    submit = SubmitField('Submit')