from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ddf522942d93"
down_revision: Union[str, None] = "61d5ea069fed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_enum_labels(conn: sa.engine.Connection) -> list[str]:
    result = conn.execute(
        sa.text(
            """
            SELECT enumlabel
            FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'process_status'
            ORDER BY enumsortorder
            """
        )
    )
    return [row[0] for row in result]


def upgrade() -> None:
    conn = op.get_bind()
    labels = _get_enum_labels(conn)
    if any(label.lower() == "cancelled" for label in labels):
        return

    new_label = "CANCELLED" if labels and all(label.isupper() for label in labels) else "cancelled"
    op.execute(sa.text(f"ALTER TYPE process_status ADD VALUE '{new_label}'"))


def downgrade() -> None:
    conn = op.get_bind()
    labels = _get_enum_labels(conn)
    filtered = [label for label in labels if label.lower() != "cancelled"]

    if len(filtered) == len(labels):
        return

    op.execute(sa.text("ALTER TYPE process_status RENAME TO process_status_old"))
    new_labels = ", ".join(f"'{label}'" for label in filtered)
    op.execute(sa.text(f"CREATE TYPE process_status AS ENUM ({new_labels})"))
    op.execute(
        sa.text("""
        ALTER TABLE routes
        ALTER COLUMN status
        TYPE process_status
        USING status::text::process_status
    """)
    )
    op.execute(sa.text("DROP TYPE process_status_old"))
