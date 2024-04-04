"""add articles

Revision ID: 9a6e55094da4
Revises: a2e2130e0393
Create Date: 2024-04-04 12:01:40.594403

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a6e55094da4'
down_revision = 'a2e2130e0393'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('article',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('url_path', sa.String(length=255), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('author_name', sa.String(length=255), nullable=False),
    sa.Column('category', sa.String(length=140), nullable=False),
    sa.Column('key_topics', sa.TEXT(), nullable=False),
    sa.Column('sub_categories', sa.TEXT(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_article_created'), ['created'], unique=False)
        batch_op.create_index(batch_op.f('ix_article_user_id'), ['user_id'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_article_user_id'))
        batch_op.drop_index(batch_op.f('ix_article_created'))

    op.drop_table('article')
    # ### end Alembic commands ###
