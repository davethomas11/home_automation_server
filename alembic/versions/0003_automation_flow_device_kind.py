"""Add device_kind to automation_flow and remove Apple-TV-only FK

Revision ID: 0003_automation_flow_device_kind
Revises: 0002_add_samsung_tv_device
Create Date: 2026-03-12 00:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "0003_automation_flow_device_kind"
down_revision: Union[str, None] = "0002_add_samsung_tv_device"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite-safe table rebuild to drop appletv-only foreign key and add device_kind.
    op.create_table(
        "automation_flow_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_kind", sqlmodel.AutoString(), nullable=False, server_default="apple_tv"),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.Column("trigger_type", sqlmodel.AutoString(), nullable=False),
        sa.Column("trigger_payload", sqlmodel.AutoString(), nullable=False, server_default="{}"),
        sa.Column("action_type", sqlmodel.AutoString(), nullable=False),
        sa.Column("action_payload", sqlmodel.AutoString(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO automation_flow_new (
            id, device_kind, device_id, name, trigger_type, trigger_payload, action_type, action_payload
        )
        SELECT
            id, 'apple_tv', device_id, name, trigger_type, trigger_payload, action_type, action_payload
        FROM automation_flow
        """
    )

    op.drop_table("automation_flow")
    op.rename_table("automation_flow_new", "automation_flow")


def downgrade() -> None:
    # Restore original Apple-TV-only FK shape.
    op.create_table(
        "automation_flow_old",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.Column("trigger_type", sqlmodel.AutoString(), nullable=False),
        sa.Column("trigger_payload", sqlmodel.AutoString(), nullable=False, server_default="{}"),
        sa.Column("action_type", sqlmodel.AutoString(), nullable=False),
        sa.Column("action_payload", sqlmodel.AutoString(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["device_id"], ["appletv_device.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO automation_flow_old (
            id, device_id, name, trigger_type, trigger_payload, action_type, action_payload
        )
        SELECT
            id, device_id, name, trigger_type, trigger_payload, action_type, action_payload
        FROM automation_flow
        WHERE device_kind = 'apple_tv'
        """
    )

    op.drop_table("automation_flow")
    op.rename_table("automation_flow_old", "automation_flow")

