"""Protect the audit trail against update, delete and truncate.

Revision ID: 9b420e3b6c10
Revises: 34852fabf912
"""

from alembic import op

revision = "9b420e3b6c10"
down_revision = "34852fabf912"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE FUNCTION reject_audit_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Audit records are immutable';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER audit_no_mutation BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
    """)
    op.execute("""
        CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_mutation();
    """)
    op.create_check_constraint("users_failed_logins_nonnegative", "users", "failed_logins >= 0")


def downgrade():
    op.drop_constraint("users_failed_logins_nonnegative", "users", type_="check")
    op.execute("DROP TRIGGER audit_no_truncate ON audit_events")
    op.execute("DROP TRIGGER audit_no_mutation ON audit_events")
    op.execute("DROP FUNCTION reject_audit_mutation()")
