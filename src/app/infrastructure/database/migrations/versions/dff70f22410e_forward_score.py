"""forward score

Revision ID: dff70f22410e
Revises: 61d5ea069fed
Create Date: 2025-09-10 12:42:36.270008

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'dff70f22410e'
down_revision: Union[str, None] = '61d5ea069fed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('forwarded', sa.Column('score', sa.FLOAT(), nullable=True))


def downgrade() -> None:
    op.drop_column('forwarded', 'score')
