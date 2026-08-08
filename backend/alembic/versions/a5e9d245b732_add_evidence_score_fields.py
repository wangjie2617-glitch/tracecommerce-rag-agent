"""add evidence score fields

Revision ID: a5e9d245b732
Revises: 5790b37ca7a1
Create Date: 2026-07-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a5e9d245b732"
down_revision: str | Sequence[str] | None = "5790b37ca7a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rag_requests",
        sa.Column("evidence_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "rag_requests",
        sa.Column(
            "evidence_level",
            sa.String(length=20),
            server_default="insufficient",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE rag_requests
        SET evidence_score = confidence,
            evidence_level = CASE
                WHEN grounded IS FALSE THEN 'insufficient'
                WHEN confidence >= 0.65 THEN 'high'
                WHEN confidence >= 0.35 THEN 'medium'
                ELSE 'low'
            END
        """
    )
    op.alter_column("rag_requests", "evidence_score", server_default=None)
    op.alter_column("rag_requests", "evidence_level", server_default=None)


def downgrade() -> None:
    op.drop_column("rag_requests", "evidence_level")
    op.drop_column("rag_requests", "evidence_score")
