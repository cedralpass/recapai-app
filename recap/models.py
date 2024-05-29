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
from recap import Config
import jwt
from time import time
import json
from flask import current_app



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
    
    #get articles for user
    def get_articles(self,page=1, per_page=2, category=None):
        #select all articles of the current_user
        stmt = sa.select(Article).where(Article.user_id == self.id).order_by(Article.id.desc())
        if category:
            stmt = stmt.where(Article.category == category)
        articles = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
        return articles
   
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
           Config.RECAP_SECRET_KEY, algorithm='HS256')
    
    def get_categories(self):
        groupings =  db.session.query(
        Article.category,
        sa.func.count(Article.id).label('count')
        ).filter(
            Article.user_id == self.id
            ).group_by(
                Article.category
                ).order_by(
                    sa.desc('count')
                    ).all()
        
        current_app.logger.debug(groupings)
        return groupings

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, Config.RECAP_SECRET_KEY,
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return db.session.get(User, id)
    
        
        
    

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
    classified: so.Mapped[datetime] = so.mapped_column(sa.DateTime(), nullable=True)

    def __repr__(self):
        return '<Article {}>'.format(self.url_path)
    @staticmethod
    def get_article_by_url_path(url_path,user_id):
        #select all articles of the current_user
        stmt = sa.select(Article).where(Article.user_id == user_id).where(Article.url_path==url_path).order_by(Article.id.desc())
        article= db.session.execute(stmt).scalar()
        return article
    
    def get_sub_categories_json(self):
        sub_categories_json = None
        if self.sub_categories is not None:
            sub_categories_json = json.loads(self.sub_categories)
        return sub_categories_json
    
    def get_key_topics_json(self):
        key_topics_json = None
        if self.key_topics is not None:
            key_topics_json = json.loads(self.key_topics)
        return key_topics_json

class Topic(db.Model):
    id: so.Mapped[Uuid] = so.mapped_column(sa.Uuid(),primary_key=True, default=lambda: uuid.uuid4())
    name: so.Mapped[str] = so.mapped_column(sa.String(140))
    definition: so.Mapped[str] = so.mapped_column(sa.String(4000), nullable=True)

    def __repr__(self):
        return '<Topic {}>'.format(self.name)