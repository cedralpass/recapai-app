import urllib.parse

import sqlalchemy as sa
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError

from recap import db
from recap.models import User


class ArticleForm(FlaskForm):
    url_path = StringField(
        "Let AI summarize an article for reading later",
        validators=[DataRequired()],
        render_kw={"placeholder": "https://good.blog.com/interesting-article"},
    )
    submit = SubmitField("Submit")

    def validate_url_path(self, field):
        try:
            parsed = urllib.parse.urlparse(field.data or "")
        except Exception:
            raise ValidationError("Please enter a valid URL.")
        if parsed.scheme != "https":
            raise ValidationError(
                "Only HTTPS URLs are accepted. " "Please check the link starts with https:// and try again."
            )
        if not parsed.hostname:
            raise ValidationError("Please enter a valid URL including a hostname.")
