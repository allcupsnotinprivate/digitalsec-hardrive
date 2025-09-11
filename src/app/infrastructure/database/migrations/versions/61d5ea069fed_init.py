"""init

Revision ID: 61d5ea069fed
Revises:
Create Date: 2025-07-18 22:37:46.498852

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "61d5ea069fed"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ProcessStatusEnum = postgresql.ENUM(
    "PENDING", "IN_PROGRESS", "COMPLETED", "TIMEOUT", "FAILED", name="process_status", create_type=False
)


def upgrade() -> None:
    ProcessStatusEnum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("name", sa.VARCHAR(length=124), nullable=False),
        sa.Column("description", sa.VARCHAR(length=512), nullable=True),
        sa.Column("embedding", VECTOR(dim=1024), nullable=True),
        sa.Column("is_active", sa.BOOLEAN(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("is_default_recipient", sa.BOOLEAN(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("name", sa.VARCHAR(length=124), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "document_chunks",
        sa.Column("content", sa.VARCHAR(), nullable=False),
        sa.Column("embedding", VECTOR(dim=1024), nullable=False),
        sa.Column("hash", postgresql.BYTEA(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["document_chunks.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "routes",
        sa.Column("status", ProcessStatusEnum, nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["agents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "forwarded",
        sa.Column("purpose", sa.VARCHAR(length=52), nullable=True),
        sa.Column("is_valid", sa.BOOLEAN(), nullable=True),
        sa.Column("is_hidden", sa.BOOLEAN(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=True),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("route_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("score", sa.FLOAT(), nullable=True),
        sa.CheckConstraint("sender_id != recipient_id", name="ck_forwarded_sender_recipient_different"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["agents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["agents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("forwarded")
    op.drop_table("routes")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("agents")
    ProcessStatusEnum.drop(op.get_bind(), checkfirst=True)
