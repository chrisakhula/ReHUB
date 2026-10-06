"""Phase 6 Billing Models

Revision ID: gg2345678901
Revises: ff1234567890
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'gg2345678901'
down_revision = 'ff1234567890'
branch_labels = None
depends_on = None

def upgrade():
    # Drop old billing tables
    op.drop_table('payments')
    op.drop_table('invoices')
    op.drop_table('payers')
    # Drop enum types if they exist (PostgreSQL specific)
    op.execute("DROP TYPE IF EXISTS invoicestatus;")

    # Create new billing tables
    op.create_table('billing_services',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_services_code'), 'billing_services', ['code'], unique=True)
    op.create_index(op.f('ix_billing_services_facility_id'), 'billing_services', ['facility_id'], unique=False)

    op.create_table('billing_programme_packages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_programme_packages_facility_id'), 'billing_programme_packages', ['facility_id'], unique=False)

    op.create_table('billing_payers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('payer_type', sa.String(length=50), nullable=False),
        sa.Column('contact_person', sa.String(length=150), nullable=False),
        sa.Column('contact_email', sa.String(length=150), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=False),
        sa.Column('billing_address', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_payers_facility_id'), 'billing_payers', ['facility_id'], unique=False)

    op.create_table('billing_price_lists',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('service_id', sa.UUID(), nullable=True),
        sa.Column('package_id', sa.UUID(), nullable=True),
        sa.Column('payer_category', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['package_id'], ['billing_programme_packages.id'], ),
        sa.ForeignKeyConstraint(['service_id'], ['billing_services.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_price_lists_facility_id'), 'billing_price_lists', ['facility_id'], unique=False)

    op.create_table('billing_client_payers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('payer_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('policy_number', sa.String(length=100), nullable=False),
        sa.Column('coverage_details', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['payer_id'], ['billing_payers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_client_payers_client_id'), 'billing_client_payers', ['client_id'], unique=False)
    op.create_index(op.f('ix_billing_client_payers_payer_id'), 'billing_client_payers', ['payer_id'], unique=False)

    op.create_table('billing_invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=True),
        sa.Column('payer_id', sa.UUID(), nullable=True),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['payer_id'], ['billing_payers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_invoices_admission_id'), 'billing_invoices', ['admission_id'], unique=False)
    op.create_index(op.f('ix_billing_invoices_client_id'), 'billing_invoices', ['client_id'], unique=False)
    op.create_index(op.f('ix_billing_invoices_facility_id'), 'billing_invoices', ['facility_id'], unique=False)
    op.create_index(op.f('ix_billing_invoices_invoice_number'), 'billing_invoices', ['invoice_number'], unique=True)
    op.create_index(op.f('ix_billing_invoices_payer_id'), 'billing_invoices', ['payer_id'], unique=False)

    op.create_table('billing_payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('payer_id', sa.UUID(), nullable=True),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('transaction_reference', sa.String(length=100), nullable=False),
        sa.Column('payment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['payer_id'], ['billing_payers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_payments_client_id'), 'billing_payments', ['client_id'], unique=False)
    op.create_index(op.f('ix_billing_payments_facility_id'), 'billing_payments', ['facility_id'], unique=False)
    op.create_index(op.f('ix_billing_payments_payer_id'), 'billing_payments', ['payer_id'], unique=False)
    op.create_index(op.f('ix_billing_payments_transaction_reference'), 'billing_payments', ['transaction_reference'], unique=False)

    op.create_table('billing_adjustments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('adjustment_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_adjustments_facility_id'), 'billing_adjustments', ['facility_id'], unique=False)
    op.create_index(op.f('ix_billing_adjustments_invoice_id'), 'billing_adjustments', ['invoice_id'], unique=False)

    op.create_table('billing_credit_notes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('credit_number', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('issued_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ),
        sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_credit_notes_credit_number'), 'billing_credit_notes', ['credit_number'], unique=True)
    op.create_index(op.f('ix_billing_credit_notes_facility_id'), 'billing_credit_notes', ['facility_id'], unique=False)
    op.create_index(op.f('ix_billing_credit_notes_invoice_id'), 'billing_credit_notes', ['invoice_id'], unique=False)

    op.create_table('billing_invoice_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('service_id', sa.UUID(), nullable=True),
        sa.Column('package_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ),
        sa.ForeignKeyConstraint(['package_id'], ['billing_programme_packages.id'], ),
        sa.ForeignKeyConstraint(['service_id'], ['billing_services.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_invoice_items_invoice_id'), 'billing_invoice_items', ['invoice_id'], unique=False)

    op.create_table('billing_mpesa_transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('transaction_reference', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payer_id', sa.UUID(), nullable=True),
        sa.Column('invoice_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('reconciled_payment_id', sa.UUID(), nullable=True),
        sa.Column('raw_payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ),
        sa.ForeignKeyConstraint(['payer_id'], ['billing_payers.id'], ),
        sa.ForeignKeyConstraint(['reconciled_payment_id'], ['billing_payments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_mpesa_transactions_facility_id'), 'billing_mpesa_transactions', ['facility_id'], unique=False)
    op.create_index(op.f('ix_billing_mpesa_transactions_transaction_reference'), 'billing_mpesa_transactions', ['transaction_reference'], unique=True)

    op.create_table('billing_payment_allocations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('payment_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('allocated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('allocated_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['allocated_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ),
        sa.ForeignKeyConstraint(['payment_id'], ['billing_payments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_payment_allocations_invoice_id'), 'billing_payment_allocations', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_billing_payment_allocations_payment_id'), 'billing_payment_allocations', ['payment_id'], unique=False)

    op.create_table('billing_receipts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('payment_id', sa.UUID(), nullable=False),
        sa.Column('receipt_number', sa.String(length=50), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('issued_by', sa.UUID(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['payment_id'], ['billing_payments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_receipts_payment_id'), 'billing_receipts', ['payment_id'], unique=False)
    op.create_index(op.f('ix_billing_receipts_receipt_number'), 'billing_receipts', ['receipt_number'], unique=True)

    op.create_table('billing_refunds',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('payment_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('refund_method', sa.String(length=50), nullable=False),
        sa.Column('transaction_reference', sa.String(length=100), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['payment_id'], ['billing_payments.id'], ),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_refunds_facility_id'), 'billing_refunds', ['facility_id'], unique=False)
    op.create_index(op.f('ix_billing_refunds_payment_id'), 'billing_refunds', ['payment_id'], unique=False)

    op.create_table('billing_write_offs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('approved_by', sa.UUID(), nullable=False),
        sa.Column('written_off_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_write_offs_facility_id'), 'billing_write_offs', ['facility_id'], unique=False)
    op.create_index(op.f('ix_billing_write_offs_invoice_id'), 'billing_write_offs', ['invoice_id'], unique=False)

def downgrade():
    pass
