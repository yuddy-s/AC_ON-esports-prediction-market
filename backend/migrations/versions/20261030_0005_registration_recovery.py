"""Retain signer, challenge fingerprints, and fixture snapshot in registrar audit.

Revision ID: 20261030_0005
Revises: 20261029_0004
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261030_0005"
down_revision: str | None = "20261029_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("fixture_registration_jobs", sa.Column("authorization_challenge_id", sa.Integer(), nullable=True))
    op.add_column("fixture_registration_jobs", sa.Column("authorization_nonce_hash", sa.String(64), nullable=True))
    op.add_column("fixture_registration_jobs", sa.Column("authorization_message_hash", sa.String(64), nullable=True))
    op.add_column("registration_job_events", sa.Column("requested_by", sa.String(42), nullable=True))
    op.add_column("registration_job_events", sa.Column("challenge_id", sa.Integer(), nullable=True))
    op.add_column("registration_job_events", sa.Column("nonce_hash", sa.String(64), nullable=True))
    op.add_column("registration_job_events", sa.Column("message_hash", sa.String(64), nullable=True))
    op.add_column("registration_job_events", sa.Column("fixture_snapshot", sa.JSON(), nullable=True))
    # Older events remain null: assigning the current mutable job requester to
    # them could falsely attribute an earlier authorization after recovery.


def downgrade() -> None:
    op.drop_column("registration_job_events", "fixture_snapshot")
    op.drop_column("registration_job_events", "message_hash")
    op.drop_column("registration_job_events", "nonce_hash")
    op.drop_column("registration_job_events", "challenge_id")
    op.drop_column("registration_job_events", "requested_by")
    op.drop_column("fixture_registration_jobs", "authorization_message_hash")
    op.drop_column("fixture_registration_jobs", "authorization_nonce_hash")
    op.drop_column("fixture_registration_jobs", "authorization_challenge_id")
