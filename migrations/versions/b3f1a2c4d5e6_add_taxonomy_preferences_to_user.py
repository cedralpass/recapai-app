"""add taxonomy_preferences to user

Revision ID: b3f1a2c4d5e6
Revises: 2aaf7ced1217
Create Date: 2026-05-16 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b3f1a2c4d5e6"
down_revision = "2aaf7ced1217"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("taxonomy_preferences", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("taxonomy_preferences")
