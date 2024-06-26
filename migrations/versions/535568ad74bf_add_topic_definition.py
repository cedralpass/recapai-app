"""add topic definition

Revision ID: 535568ad74bf
Revises: cdfd272a7375
Create Date: 2024-04-04 14:03:44.541968

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '535568ad74bf'
down_revision = 'cdfd272a7375'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('topic', schema=None) as batch_op:
        batch_op.add_column(sa.Column('definition', sa.String(length=4000), nullable=True))
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=140),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('topic', schema=None) as batch_op:
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=140),
               nullable=True)
        batch_op.drop_column('definition')

    # ### end Alembic commands ###
