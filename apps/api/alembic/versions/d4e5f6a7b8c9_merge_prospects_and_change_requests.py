"""merge the prospect and client-review migration branches

Revision ID: d4e5f6a7b8c9
Revises: 0f2a9f6d7b11, c41f7d2a9b13
"""

from typing import Sequence, Union


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = ("0f2a9f6d7b11", "c41f7d2a9b13")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge the two independent feature migrations into one release head."""
    pass


def downgrade() -> None:
    """Split the merge; parent migrations handle their own downgrade work."""
    pass
