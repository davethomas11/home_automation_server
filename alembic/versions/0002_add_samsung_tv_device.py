"""Add Samsung TV device table

Revision ID: 0002_add_samsung_tv_device
Revises: 0001_initial
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "0002_add_samsung_tv_device"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("samsung_tv_device"):
        op.create_table(
            "samsung_tv_device",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sqlmodel.AutoString(), nullable=False),
            sa.Column("ip_address", sqlmodel.AutoString(), nullable=False),
            sa.Column("model_year", sa.Integer(), nullable=False),
            sa.Column("port", sa.Integer(), nullable=False, server_default="8002"),
            sa.Column("token", sqlmodel.AutoString(), nullable=True),
            sa.Column("mac_address", sqlmodel.AutoString(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    index_names = {idx["name"] for idx in inspector.get_indexes("samsung_tv_device")}
    if "ix_samsung_tv_device_name" not in index_names:
        op.create_index("ix_samsung_tv_device_name", "samsung_tv_device", ["name"])
    if "ix_samsung_tv_device_ip_address" not in index_names:
        op.create_index("ix_samsung_tv_device_ip_address", "samsung_tv_device", ["ip_address"])


def downgrade() -> None:
    op.drop_index("ix_samsung_tv_device_ip_address", table_name="samsung_tv_device")
    op.drop_index("ix_samsung_tv_device_name", table_name="samsung_tv_device")
    op.drop_table("samsung_tv_device")

