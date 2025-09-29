"""s3

Revision ID: 33bde010d27a
Revises: ddf522942d93
Create Date: 2025-09-29 00:21:11.481981

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "33bde010d27a"
down_revision: Union[str, None] = "ddf522942d93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("storage_bucket", sa.VARCHAR(length=63), nullable=False, server_default=sa.text("'default-bucket'")),
    )
    op.add_column(
        "documents",
        sa.Column(
            "storage_key", sa.VARCHAR(length=512), nullable=False, server_default=sa.text("gen_random_uuid()::text")
        ),
    )
    op.add_column("documents", sa.Column("content_type", sa.VARCHAR(length=255), nullable=True))
    op.add_column("documents", sa.Column("file_size", sa.BIGINT(), nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("original_filename", sa.VARCHAR(length=255), nullable=True))
    op.add_column("documents", sa.Column("storage_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_unique_constraint(None, "documents", ["storage_key"])

    op.alter_column("documents", "storage_bucket", server_default=None)
    op.alter_column("documents", "storage_key", server_default=None)
    op.alter_column("documents", "file_size", server_default=None)


def downgrade() -> None:
    op.drop_constraint(None, "documents", type_="unique")  # type: ignore[arg-type]
    op.drop_column("documents", "storage_metadata")
    op.drop_column("documents", "original_filename")
    op.drop_column("documents", "file_size")
    op.drop_column("documents", "content_type")
    op.drop_column("documents", "storage_key")
    op.drop_column("documents", "storage_bucket")
