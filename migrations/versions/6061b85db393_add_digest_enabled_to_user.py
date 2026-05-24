"""add digest_enabled to user

Revision ID: 6061b85db393
Revises: 0dbf2a19c462
Create Date: 2026-05-23 18:11:46.065632

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6061b85db393"
down_revision = "0dbf2a19c462"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("digest_enabled", sa.Boolean(), nullable=False, server_default="true"))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("digest_enabled")
