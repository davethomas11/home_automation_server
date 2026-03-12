"""
SQLModel ORM models for all database tables.
"""

from typing import Optional
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel


# ---------------------------------------------------------------------------
# AppleTVDevice
# ---------------------------------------------------------------------------

class AppleTVDeviceBase(SQLModel):
    name: str = Field(index=True)
    identifier: str = Field(unique=True, index=True)  # pyatv device identifier
    ip_address: str


class AppleTVDevice(AppleTVDeviceBase, table=True):
    __tablename__ = "appletv_device"

    id: Optional[int] = Field(default=None, primary_key=True)

    pairings: Mapped[list["AppleTVPairing"]] = Relationship(back_populates="device")
    automation_flows: Mapped[list["AutomationFlow"]] = Relationship(back_populates="device")
    app_launch_configs: Mapped[list["AppLaunchConfig"]] = Relationship(back_populates="device")


class AppleTVDeviceCreate(AppleTVDeviceBase):
    pass


class AppleTVDeviceRead(AppleTVDeviceBase):
    id: int


# ---------------------------------------------------------------------------
# AppleTVPairing
# ---------------------------------------------------------------------------

class AppleTVPairingBase(SQLModel):
    device_id: int = Field(foreign_key="appletv_device.id")
    protocol: str  # "MRP" | "Companion" | "AirPlay"
    credentials: str  # serialised credential string from pyatv


class AppleTVPairing(AppleTVPairingBase, table=True):
    __tablename__ = "appletv_pairing"

    id: Optional[int] = Field(default=None, primary_key=True)

    device: Mapped[Optional["AppleTVDevice"]] = Relationship(back_populates="pairings")


class AppleTVPairingCreate(AppleTVPairingBase):
    pass


class AppleTVPairingRead(AppleTVPairingBase):
    id: int


# ---------------------------------------------------------------------------
# AutomationFlow
# ---------------------------------------------------------------------------

class AutomationFlowBase(SQLModel):
    device_id: int = Field(foreign_key="appletv_device.id")
    name: str
    trigger_type: str  # "webhook" | "schedule" | "manual"
    trigger_payload: str = "{}"  # JSON string
    action_type: str  # "launch_app" | "remote_command" | "power"
    action_payload: str = "{}"  # JSON string


class AutomationFlow(AutomationFlowBase, table=True):
    __tablename__ = "automation_flow"

    id: Optional[int] = Field(default=None, primary_key=True)

    device: Mapped[Optional["AppleTVDevice"]] = Relationship(back_populates="automation_flows")


class AutomationFlowCreate(AutomationFlowBase):
    pass


class AutomationFlowRead(AutomationFlowBase):
    id: int


# ---------------------------------------------------------------------------
# AppLaunchConfig
# ---------------------------------------------------------------------------

class AppLaunchConfigBase(SQLModel):
    device_id: int = Field(foreign_key="appletv_device.id")
    app_name: str
    bundle_id: str  # e.g. "com.netflix.Netflix"


class AppLaunchConfig(AppLaunchConfigBase, table=True):
    __tablename__ = "app_launch_config"

    id: Optional[int] = Field(default=None, primary_key=True)

    device: Mapped[Optional["AppleTVDevice"]] = Relationship(back_populates="app_launch_configs")


class AppLaunchConfigCreate(AppLaunchConfigBase):
    pass


class AppLaunchConfigRead(AppLaunchConfigBase):
    id: int
