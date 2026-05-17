"""add article embedding column for vector search

Revision ID: a1b2c3d4e5f6
Revises: b3f1a2c4d5e6
Create Date: 2026-05-16 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

try:
    from pgvector.sqlalchemy import Vector

    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False

revision = "a1b2c3d4e5f6"
down_revision = "b3f1a2c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("article", sa.Column("embedding", Vector(1536), nullable=True))
    op.execute(
        """
        CREATE INDEX article_embedding_hnsw_idx
        ON article
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS article_embedding_hnsw_idx")
    op.drop_column("article", "embedding")
