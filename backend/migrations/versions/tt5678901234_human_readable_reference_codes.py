"""Add human-readable reference codes across ReHUB entities.

Revision ID: tt5678901234
Revises: ss4567890123
Create Date: 2026-10-14 17:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'tt5678901234'
down_revision = 'ss4567890123'
branch_labels = None
depends_on = None

ENTITIES = [
    # (table_name, prefix, digits, use_year, custom_name)
    ('medications', 'MED', 5, False, 'reference_code'),
    ('prescriptions', 'RX', 4, True, 'reference_code'),
    ('medication_administrations', 'MAR', 4, True, 'reference_code'),
    ('clinical_encounters', 'ENC', 4, True, 'reference_code'),
    ('clinical_orders', 'MO', 4, True, 'reference_code'),
    ('clinical_lab_requests', 'LAB', 4, True, 'reference_code'),
    ('referrals', 'REF', 4, True, 'reference_code'),
    ('treatment_plans', 'TP', 4, True, 'reference_code'),
    ('instrument_assessments', 'ASM', 4, True, 'reference_code'),
    ('biopsychosocial_assessments', 'ASM', 4, True, 'reference_code'),
    ('risk_assessments', 'ASM', 4, True, 'reference_code'),
    ('residential_incidents', 'INC', 4, True, 'reference_code'),
    ('residential_visitors', 'VIS', 4, True, 'reference_code'),
    ('discharge_plans', 'DIS', 4, True, 'reference_code'),
    ('discharge_aftercare_cases', 'AFC', 4, True, 'reference_code'),
]


def upgrade() -> None:
    # 1. Expand record_numbers.kind length
    op.alter_column('record_numbers', 'kind', type_=sa.String(40), existing_type=sa.String(20))

    conn = op.get_bind()

    # Disable audit/care history trigger for backfill updates if in PostgreSQL
    is_postgres = conn.dialect.name == "postgresql"
    if is_postgres:
        conn.execute(sa.text("SET session_replication_role = replica;"))

    try:
        # 2. Add reference_code column as nullable first
        for table_name, prefix, digits, use_year, col_name in ENTITIES:
            op.add_column(table_name, sa.Column(col_name, sa.String(50), nullable=True))

            # Backfill existing rows
            rows = conn.execute(sa.text(f"SELECT id FROM {table_name} ORDER BY created_at ASC, id ASC")).fetchall()
            for idx, row in enumerate(rows, start=1):
                row_id = str(row[0])
                # Special case for existing medication in dev/prod
                if table_name == 'medications' and row_id == '57ea36c6-0bab-464b-aaf6-96a2f437d7cf':
                    code = "MED-00127"
                elif use_year:
                    code = f"{prefix}-2026-{idx:0{digits}d}"
                else:
                    code = f"{prefix}-{idx:0{digits}d}"
                conn.execute(
                    sa.text(f"UPDATE {table_name} SET {col_name} = :code WHERE id = :id"),
                    {"code": code, "id": row[0]}
                )

            # 3. Alter to NOT NULL and create index
            op.alter_column(table_name, col_name, nullable=False)
            op.create_index(f"ix_{table_name}_{col_name}", table_name, [col_name])

        # Add unique constraints where strictly appropriate
        op.create_unique_constraint("uq_medications_facility_ref", "medications", ["facility_id", "reference_code"])
        op.create_unique_constraint("uq_prescriptions_facility_ref", "prescriptions", ["facility_id", "reference_code"])
        op.create_unique_constraint("uq_referrals_facility_ref", "referrals", ["facility_id", "reference_code"])
    finally:
        if is_postgres:
            conn.execute(sa.text("SET session_replication_role = DEFAULT;"))


def downgrade() -> None:
    op.drop_constraint("uq_referrals_facility_ref", "referrals", type_="unique")
    op.drop_constraint("uq_prescriptions_facility_ref", "prescriptions", type_="unique")
    op.drop_constraint("uq_medications_facility_ref", "medications", type_="unique")

    for table_name, _, _, _, col_name in reversed(ENTITIES):
        op.drop_index(f"ix_{table_name}_{col_name}", table_name=table_name)
        op.drop_column(table_name, col_name)

    op.alter_column('record_numbers', 'kind', type_=sa.String(20), existing_type=sa.String(40))
