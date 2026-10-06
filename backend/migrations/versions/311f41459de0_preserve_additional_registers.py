"""Protect additional intake revision and pharmacy count registers."""

from alembic import op

revision = "311f41459de0"
down_revision = "e20658b750bf"
branch_labels = None
depends_on = None


def upgrade():
    for table in ["admission_intake_revisions", "pharmacy_stock_counts"]:
        op.execute(
            f'CREATE TRIGGER preserve_history BEFORE UPDATE OR DELETE ON "{table}" '
            "FOR EACH ROW EXECUTE FUNCTION preserve_care_history()"
        )
        op.execute(
            f'CREATE TRIGGER preserve_history_truncate BEFORE TRUNCATE ON "{table}" '
            "FOR EACH STATEMENT EXECUTE FUNCTION preserve_care_history()"
        )


def downgrade():
    for table in ["admission_intake_revisions", "pharmacy_stock_counts"]:
        op.execute(f'DROP TRIGGER preserve_history_truncate ON "{table}"')
        op.execute(f'DROP TRIGGER preserve_history ON "{table}"')
