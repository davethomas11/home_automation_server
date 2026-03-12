"""Initial schema – create all tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- appletv_device ---
    op.create_table(
        "appletv_device",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.Column("identifier", sqlmodel.AutoString(), nullable=False),
        sa.Column("ip_address", sqlmodel.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index("ix_appletv_device_name", "appletv_device", ["name"])
    op.create_index("ix_appletv_device_identifier", "appletv_device", ["identifier"])

    # --- appletv_pairing ---
    op.create_table(
        "appletv_pairing",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sqlmodel.AutoString(), nullable=False),
        sa.Column("credentials", sqlmodel.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["appletv_device.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- automation_flow ---
    op.create_table(
        "automation_flow",
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

    # --- app_launch_config ---
    op.create_table(
        "app_launch_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("app_name", sqlmodel.AutoString(), nullable=False),
        sa.Column("bundle_id", sqlmodel.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["appletv_device.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("app_launch_config")
    op.drop_table("automation_flow")
    op.drop_table("appletv_pairing")
    op.drop_index("ix_appletv_device_identifier", table_name="appletv_device")
    op.drop_index("ix_appletv_device_name", table_name="appletv_device")
    op.drop_table("appletv_device")

