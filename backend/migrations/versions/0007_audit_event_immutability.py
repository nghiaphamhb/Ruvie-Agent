"""Make audit events append-only."""

from alembic import op


revision = "0007_audit_event_immutability"
down_revision = "0006_revision_uploader"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("audit_events_project_id_fkey", "audit_events", type_="foreignkey")
    op.create_foreign_key(
        "fk_audit_events_project_id_projects",
        "audit_events",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        """CREATE FUNCTION ruvie_reject_audit_event_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit events are append-only';
        END;
        $$"""
    )
    op.execute(
        """CREATE TRIGGER trg_audit_events_immutable
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION ruvie_reject_audit_event_mutation()"""
    )
    op.execute(
        """CREATE TRIGGER trg_audit_events_no_truncate
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION ruvie_reject_audit_event_mutation()"""
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER trg_audit_events_immutable ON audit_events")
    op.execute("DROP FUNCTION ruvie_reject_audit_event_mutation()")
    op.drop_constraint("fk_audit_events_project_id_projects", "audit_events", type_="foreignkey")
    op.create_foreign_key(
        "audit_events_project_id_fkey",
        "audit_events",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
