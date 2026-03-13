"""
SQLModel ORM models for all database tables.
"""

from enum import Enum
from typing import Optional
import sqlalchemy as sa
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
    app_launch_configs: Mapped[list["AppLaunchConfig"]] = Relationship(back_populates="device")


class AppleTVDeviceCreate(AppleTVDeviceBase):
    pass


class AppleTVDeviceRead(AppleTVDeviceBase):
    id: int


class DeviceKind(str, Enum):
    APPLE_TV = "apple_tv"
    SAMSUNG_TV = "samsung_tv"


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
    device_kind: DeviceKind = Field(default=DeviceKind.APPLE_TV)
    device_id: int
    name: str
    trigger_type: str  # "webhook" | "schedule" | "manual"
    trigger_payload: str = "{}"  # JSON string
    action_type: str  # "launch_app" | "remote_command" | "power" | "swipe" | "sequence"
    action_payload: str = "{}"  # JSON string


class AutomationFlow(AutomationFlowBase, table=True):
    __tablename__ = "automation_flow"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Override the inherited DeviceKind field with a plain VARCHAR column so that
    # SQLAlchemy reads/writes the enum *values* ('apple_tv', 'samsung_tv') rather
    # than resolving by enum *member name* (APPLE_TV, SAMSUNG_TV), which causes a
    # LookupError on existing rows written before the Enum type was applied.
    device_kind: DeviceKind = Field(
        default=DeviceKind.APPLE_TV,
        sa_column=sa.Column(sa.String, nullable=False, default="apple_tv"),
    )




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


# ---------------------------------------------------------------------------
# SamsungTVDevice
# ---------------------------------------------------------------------------

class SamsungTVDeviceBase(SQLModel):
    name: str = Field(index=True)
    ip_address: str = Field(index=True)
    model_year: int
    port: int = 8002
    token: Optional[str] = None
    mac_address: Optional[str] = None


class SamsungTVDevice(SamsungTVDeviceBase, table=True):
    __tablename__ = "samsung_tv_device"

    id: Optional[int] = Field(default=None, primary_key=True)


class SamsungTVDeviceCreate(SamsungTVDeviceBase):
    pass


class SamsungTVDeviceRead(SamsungTVDeviceBase):
    id: int

