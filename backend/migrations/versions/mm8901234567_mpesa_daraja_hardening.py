"""Harden billing mpesa transactions with Daraja and reconciliation fields

Revision ID: mm8901234567
Revises: ll7890123456
"""

import sqlalchemy as sa
from alembic import op

revision = "mm8901234567"
down_revision = "ll7890123456"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("billing_mpesa_transactions", sa.Column("client_id", sa.Uuid(), nullable=True))
    op.add_column("billing_mpesa_transactions", sa.Column("merchant_request_id", sa.String(length=100), nullable=True))
    op.add_column("billing_mpesa_transactions", sa.Column("checkout_request_id", sa.String(length=100), nullable=True))
    op.add_column("billing_mpesa_transactions", sa.Column("response_code", sa.String(length=20), nullable=True))
    op.add_column("billing_mpesa_transactions", sa.Column("customer_message", sa.String(length=255), nullable=True))
    op.add_column(
        "billing_mpesa_transactions",
        sa.Column("reconciliation_status", sa.String(length=30), nullable=False, server_default="UNMATCHED"),
    )
    op.add_column("billing_mpesa_transactions", sa.Column("reconciled_by_id", sa.Uuid(), nullable=True))
    op.add_column("billing_mpesa_transactions", sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("billing_mpesa_transactions", sa.Column("reconciliation_notes", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_billing_mpesa_client", "billing_mpesa_transactions", "clients", ["client_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_billing_mpesa_reconciled_by", "billing_mpesa_transactions", "users", ["reconciled_by_id"], ["id"], ondelete="SET NULL"
    )

    op.create_index(op.f("ix_billing_mpesa_transactions_client_id"), "billing_mpesa_transactions", ["client_id"])
    op.create_index(op.f("ix_billing_mpesa_transactions_merchant_request_id"), "billing_mpesa_transactions", ["merchant_request_id"])
    op.create_index(op.f("ix_billing_mpesa_transactions_checkout_request_id"), "billing_mpesa_transactions", ["checkout_request_id"])
    op.create_index(op.f("ix_billing_mpesa_transactions_reconciliation_status"), "billing_mpesa_transactions", ["reconciliation_status"])


def downgrade():
    op.drop_index(op.f("ix_billing_mpesa_transactions_reconciliation_status"), table_name="billing_mpesa_transactions")
    op.drop_index(op.f("ix_billing_mpesa_transactions_checkout_request_id"), table_name="billing_mpesa_transactions")
    op.drop_index(op.f("ix_billing_mpesa_transactions_merchant_request_id"), table_name="billing_mpesa_transactions")
    op.drop_index(op.f("ix_billing_mpesa_transactions_client_id"), table_name="billing_mpesa_transactions")

    op.drop_constraint("fk_billing_mpesa_reconciled_by", "billing_mpesa_transactions", type_="foreignkey")
    op.drop_constraint("fk_billing_mpesa_client", "billing_mpesa_transactions", type_="foreignkey")

    op.drop_column("billing_mpesa_transactions", "reconciliation_notes")
    op.drop_column("billing_mpesa_transactions", "reconciled_at")
    op.drop_column("billing_mpesa_transactions", "reconciled_by_id")
    op.drop_column("billing_mpesa_transactions", "reconciliation_status")
    op.drop_column("billing_mpesa_transactions", "customer_message")
    op.drop_column("billing_mpesa_transactions", "response_code")
    op.drop_column("billing_mpesa_transactions", "checkout_request_id")
    op.drop_column("billing_mpesa_transactions", "merchant_request_id")
    op.drop_column("billing_mpesa_transactions", "client_id")
