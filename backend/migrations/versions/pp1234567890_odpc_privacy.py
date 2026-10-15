"""ODPC privacy, data protection, retention policies and export requests

Revision ID: pp1234567890
Revises: oo0123456789
"""

import uuid
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision = "pp1234567890"
down_revision = "oo0123456789"
branch_labels = None
depends_on = None


def upgrade():
    # 1. data_subject_requests
    op.create_table(
        "data_subject_requests",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("request_number", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("request_type", sa.String(50), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, default="RECEIVED", index=True),
        sa.Column("channel", sa.String(50), nullable=False, default="IN_PERSON"),
        sa.Column("subject_name", sa.String(200), nullable=False),
        sa.Column("subject_contact", sa.String(150), nullable=True),
        sa.Column("request_details", sa.Text(), nullable=False),
        sa.Column("verification_method", sa.String(100), nullable=True),
        sa.Column("dpo_notes", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )

    # 2. data_breaches
    op.create_table(
        "data_breaches",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("incident_number", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("incident_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False, index=True),
        sa.Column("odpc_notified", sa.Boolean(), nullable=False, default=False),
        sa.Column("odpc_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("odpc_reference_number", sa.String(100), nullable=True),
        sa.Column("data_subjects_notified", sa.Boolean(), nullable=False, default=False),
        sa.Column("affected_categories", JSON(), nullable=False),
        sa.Column("estimated_affected_count", sa.Integer(), nullable=False, default=0),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("containment_actions", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("remedial_measures", sa.Text(), nullable=True),
        sa.Column("dpo_signoff_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dpo_signoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="CONTAINED", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )

    # 3. retention_policies
    op.create_table(
        "retention_policies",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("record_type", sa.String(100), nullable=False, index=True),
        sa.Column("retention_period_years", sa.Integer(), nullable=False),
        sa.Column("legal_basis", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, default=""),
        sa.Column("status", sa.String(50), nullable=False, default="ACTIVE", index=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )

    # 4. export_requests
    op.create_table(
        "export_requests",
        sa.Column("id", sa.Uuid(), primary_key=True, default=uuid.uuid4),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("export_type", sa.String(50), nullable=False, index=True),
        sa.Column("filters", JSON(), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False, default=0),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("format", sa.String(20), nullable=False, default="CSV"),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="PENDING_APPROVAL", index=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )

    # Seed permissions
    permissions = [
        ("privacy.view", "View ODPC privacy records, requests and breach logs"),
        ("privacy.manage", "Manage DSAR, consent withdrawals, and breach notifications"),
        ("privacy.dpo", "Data Protection Officer signoff and statutory reporting"),
        ("client.export", "Export client registry data"),
        ("clinical.export", "Export clinical health records"),
        ("finance.export", "Export financial and accounting records"),
        ("reports.export", "Export institutional reports"),
    ]
    for code, desc in permissions:
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, description, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :code, :desc, now(), now()) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(code=code, desc=desc)
        )


def downgrade():
    op.drop_table("export_requests")
    op.drop_table("retention_policies")
    op.drop_table("data_breaches")
    op.drop_table("data_subject_requests")
