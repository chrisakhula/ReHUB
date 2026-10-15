"""Add background job execution logs table

Revision ID: ll7890123456
Revises: kk6789012345
"""

import sqlalchemy as sa
from alembic import op

revision = "ll7890123456"
down_revision = "kk6789012345"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "background_job_logs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("task_name", sa.String(length=150), nullable=False),
        sa.Column("celery_task_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="QUEUED"),
        sa.Column("facility_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("next_scheduled_execution", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_entity_type", sa.String(length=50), nullable=True),
        sa.Column("related_entity_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_background_job_logs_task_name"), "background_job_logs", ["task_name"])
    op.create_index(op.f("ix_background_job_logs_celery_task_id"), "background_job_logs", ["celery_task_id"])
    op.create_index(op.f("ix_background_job_logs_status"), "background_job_logs", ["status"])
    op.create_index(op.f("ix_background_job_logs_facility_id"), "background_job_logs", ["facility_id"])


def downgrade():
    op.drop_index(op.f("ix_background_job_logs_facility_id"), table_name="background_job_logs")
    op.drop_index(op.f("ix_background_job_logs_status"), table_name="background_job_logs")
    op.drop_index(op.f("ix_background_job_logs_celery_task_id"), table_name="background_job_logs")
    op.drop_index(op.f("ix_background_job_logs_task_name"), table_name="background_job_logs")
    op.drop_table("background_job_logs")
