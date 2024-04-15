from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy import Uuid
from recap import db
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin #flask_login has a user mixin that implements the 4 required methods
from recap import login_manager



class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    phone: so.Mapped[str] = so.mapped_column(sa.String(15), nullable=True)

    articles: so.WriteOnlyMapped['Article'] = so.relationship(
        back_populates='user')

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    # set password_hash
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # check password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @login_manager.user_loader
    def load_user(id):
        return db.session.get(User, int(id))
    

class Article(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id),
                                               index=True)
    created: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    url_path: so.Mapped[str] = so.mapped_column(sa.String(255))
    title: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=True)
    summary: so.Mapped[str] = so.mapped_column(sa.Text(), nullable=True)
    author_name: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=True)
    category: so.Mapped[str] = so.mapped_column(sa.String(140), nullable=True)
    key_topics: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    sub_categories: so.Mapped[str] = so.mapped_column(sa.TEXT(), nullable=True)
    user: so.Mapped[User] = so.relationship(back_populates='articles')

    def __repr__(self):
        return '<Article {}>'.format(self.url_path)

class Topic(db.Model):
    id: so.Mapped[Uuid] = so.mapped_column(sa.Uuid(),primary_key=True, default=lambda: uuid.uuid4())
    name: so.Mapped[str] = so.mapped_column(sa.String(140))
    definition: so.Mapped[str] = so.mapped_column(sa.String(4000), nullable=True)

    def __repr__(self):
        return '<Topic {}>'.format(self.name)