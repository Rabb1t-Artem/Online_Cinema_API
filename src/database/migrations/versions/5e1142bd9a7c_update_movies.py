"""update movies

Revision ID: 5e1142bd9a7c
Revises: aa1d8449d048
Create Date: 2025-02-03 15:32:05.589745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e1142bd9a7c'
down_revision: Union[str, None] = 'aa1d8449d048'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
