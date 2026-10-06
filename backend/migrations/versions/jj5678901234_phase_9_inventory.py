"""phase_9_inventory_staff_compliance

Revision ID: jj5678901234
Revises: ii4567890123
Create Date: 2026-10-06 11:31:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'jj5678901234'
down_revision = 'ii4567890123'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop old tables if they exist
    op.execute("DROP TABLE IF EXISTS staff_profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS compliance_audits CASCADE")
    op.execute("DROP TABLE IF EXISTS licences CASCADE")
    op.execute("DROP TABLE IF EXISTS compliance_registers CASCADE")
    op.execute("DROP TABLE IF EXISTS store_items CASCADE")

    # inventory_suppliers
    op.create_table('inventory_suppliers',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('contact_person', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_inventory_suppliers_facility_id'), 'inventory_suppliers', ['facility_id'], unique=False)

    # inventory_store_items
    op.create_table('inventory_store_items',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=50), nullable=False),
        sa.Column('current_stock', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reorder_level', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_inventory_store_items_facility_id'), 'inventory_store_items', ['facility_id'], unique=False)

    # inventory_purchase_orders
    op.create_table('inventory_purchase_orders',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('order_number', sa.String(length=100), nullable=False),
        sa.Column('order_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('requested_by_id', sa.UUID(), nullable=False),
        sa.Column('approved_by_id', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['inventory_suppliers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_number')
    )
    op.create_index(op.f('ix_inventory_purchase_orders_facility_id'), 'inventory_purchase_orders', ['facility_id'], unique=False)

    # inventory_stock_transactions
    op.create_table('inventory_stock_transactions',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('batch_number', sa.String(length=100), nullable=False),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference', sa.String(length=200), nullable=False),
        sa.Column('performed_by_id', sa.UUID(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['inventory_store_items.id'], ),
        sa.ForeignKeyConstraint(['performed_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_stock_transactions_facility_id'), 'inventory_stock_transactions', ['facility_id'], unique=False)

    # staff_profiles
    op.create_table('staff_profiles',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('employee_number', sa.String(length=100), nullable=False),
        sa.Column('designation', sa.String(length=100), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('qualifications', sa.Text(), nullable=False),
        sa.Column('professional_body', sa.String(length=100), nullable=False),
        sa.Column('licence_number', sa.String(length=100), nullable=False),
        sa.Column('licence_expiry', sa.Date(), nullable=True),
        sa.Column('employment_status', sa.String(length=50), nullable=False),
        sa.Column('emergency_contact', sa.String(length=200), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_number'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_staff_profiles_facility_id'), 'staff_profiles', ['facility_id'], unique=False)

    # staff_shifts
    op.create_table('staff_shifts',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('staff_id', sa.UUID(), nullable=False),
        sa.Column('shift_date', sa.Date(), nullable=False),
        sa.Column('shift_type', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attended', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['staff_id'], ['staff_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_staff_shifts_facility_id'), 'staff_shifts', ['facility_id'], unique=False)

    # compliance_registers
    op.create_table('compliance_registers',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('authority', sa.String(length=200), nullable=False),
        sa.Column('reference_number', sa.String(length=100), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('responsible_person_id', sa.UUID(), nullable=True),
        sa.Column('attachments_url', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['responsible_person_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_registers_facility_id'), 'compliance_registers', ['facility_id'], unique=False)

    # compliance_inspections
    op.create_table('compliance_inspections',
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('register_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('inspection_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('inspector_name', sa.String(length=200), nullable=False),
        sa.Column('authority', sa.String(length=200), nullable=False),
        sa.Column('findings', sa.Text(), nullable=False),
        sa.Column('corrective_actions', sa.Text(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['register_id'], ['compliance_registers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compliance_inspections_facility_id'), 'compliance_inspections', ['facility_id'], unique=False)


def downgrade() -> None:
    op.drop_table('compliance_inspections')
    op.drop_table('compliance_registers')
    op.drop_table('staff_shifts')
    op.drop_table('staff_profiles')
    op.drop_table('inventory_stock_transactions')
    op.drop_table('inventory_purchase_orders')
    op.drop_table('inventory_store_items')
    op.drop_table('inventory_suppliers')
