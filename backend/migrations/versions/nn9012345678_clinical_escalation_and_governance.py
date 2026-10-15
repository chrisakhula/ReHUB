"""Clinical crisis escalation and clinical configuration governance

Revision ID: nn9012345678
Revises: mm8901234567
"""

import sqlalchemy as sa
from alembic import op

revision = "nn9012345678"
down_revision = "mm8901234567"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Update clinical_crisis_alerts
    op.add_column("clinical_crisis_alerts", sa.Column("admission_id", sa.Uuid(), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("alert_reference", sa.String(length=50), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("trigger", sa.String(length=100), nullable=False, server_default="CLINICAL_RISK"))
    op.add_column("clinical_crisis_alerts", sa.Column("assigned_clinician_id", sa.Uuid(), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("response", sa.Text(), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("intervention", sa.Text(), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("resolution", sa.Text(), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("resolved_by_id", sa.Uuid(), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("clinical_crisis_alerts", sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("clinical_crisis_alerts", sa.Column("escalation_history", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))

    op.create_foreign_key("fk_crisis_alerts_admission", "clinical_crisis_alerts", "admissions", ["admission_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_crisis_alerts_assigned_clinician", "clinical_crisis_alerts", "users", ["assigned_clinician_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_crisis_alerts_resolved_by", "clinical_crisis_alerts", "users", ["resolved_by_id"], ["id"], ondelete="SET NULL")

    op.create_index(op.f("ix_clinical_crisis_alerts_admission_id"), "clinical_crisis_alerts", ["admission_id"])
    op.create_index(op.f("ix_clinical_crisis_alerts_alert_reference"), "clinical_crisis_alerts", ["alert_reference"], unique=True)
    op.create_index(op.f("ix_clinical_crisis_alerts_assigned_clinician_id"), "clinical_crisis_alerts", ["assigned_clinician_id"])

    # 2. Table: clinical_crisis_escalation_policies
    op.create_table(
        "clinical_crisis_escalation_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("severity", sa.String(length=30), nullable=False, server_default="CRITICAL"),
        sa.Column("tier_1_delay_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("tier_2_delay_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("notify_sms", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_email", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )

    # 3. Table: clinical_configurations
    op.create_table(
        "clinical_configurations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("key", sa.String(length=60), nullable=False, index=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.UniqueConstraint("facility_id", "key", name="uq_clinical_config_facility_key"),
    )

    # 4. Table: clinical_configuration_versions
    op.create_table(
        "clinical_configuration_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("configuration_id", sa.Uuid(), sa.ForeignKey("clinical_configurations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("schema_definition", sa.JSON(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT", index=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("configuration_id", "version_number", name="uq_clinical_config_version_number"),
    )

    op.create_foreign_key(
        "fk_clinical_configs_current_version",
        "clinical_configurations",
        "clinical_configuration_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 5. Table: clinical_approvals
    op.create_table(
        "clinical_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("configuration_version_id", sa.Uuid(), sa.ForeignKey("clinical_configuration_versions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("approver_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approver_name", sa.String(length=150), nullable=False),
        sa.Column("professional_designation", sa.String(length=150), nullable=False),
        sa.Column("professional_registration", sa.String(length=100), nullable=False),
        sa.Column("approval_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="APPROVED"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )


def downgrade():
    op.drop_table("clinical_approvals")
    op.drop_constraint("fk_clinical_configs_current_version", "clinical_configurations", type_="foreignkey")
    op.drop_table("clinical_configuration_versions")
    op.drop_table("clinical_configurations")
    op.drop_table("clinical_crisis_escalation_policies")

    op.drop_index(op.f("ix_clinical_crisis_alerts_assigned_clinician_id"), table_name="clinical_crisis_alerts")
    op.drop_index(op.f("ix_clinical_crisis_alerts_alert_reference"), table_name="clinical_crisis_alerts")
    op.drop_index(op.f("ix_clinical_crisis_alerts_admission_id"), table_name="clinical_crisis_alerts")
    op.drop_constraint("fk_crisis_alerts_resolved_by", "clinical_crisis_alerts", type_="foreignkey")
    op.drop_constraint("fk_crisis_alerts_assigned_clinician", "clinical_crisis_alerts", type_="foreignkey")
    op.drop_constraint("fk_crisis_alerts_admission", "clinical_crisis_alerts", type_="foreignkey")

    op.drop_column("clinical_crisis_alerts", "escalation_history")
    op.drop_column("clinical_crisis_alerts", "escalation_level")
    op.drop_column("clinical_crisis_alerts", "resolved_at")
    op.drop_column("clinical_crisis_alerts", "resolved_by_id")
    op.drop_column("clinical_crisis_alerts", "resolution")
    op.drop_column("clinical_crisis_alerts", "intervention")
    op.drop_column("clinical_crisis_alerts", "response")
    op.drop_column("clinical_crisis_alerts", "assigned_clinician_id")
    op.drop_column("clinical_crisis_alerts", "trigger")
    op.drop_column("clinical_crisis_alerts", "alert_reference")
    op.drop_column("clinical_crisis_alerts", "admission_id")
