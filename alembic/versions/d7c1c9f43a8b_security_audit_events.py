"""security audit events

Revision ID: d7c1c9f43a8b
Revises: e062d4e36604
Create Date: 2026-02-04 18:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7c1c9f43a8b"
down_revision: str | None = "e062d4e36604"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("endpoint", sa.String(length=256), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("auth_type", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_security_audit_events_created_at",
        "security_audit_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_security_audit_events_outcome_created_at",
        "security_audit_events",
        ["outcome", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_security_audit_events_outcome_created_at", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_created_at", table_name="security_audit_events")
    op.drop_table("security_audit_events")
