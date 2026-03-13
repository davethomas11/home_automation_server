"""Resolve a concrete device provider from device kind + device id."""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from home_automation_server.models.models import (
    AppleTVDevice,
    AppleTVPairing,
    DeviceKind,
    SamsungTVDevice,
)
from home_automation_server.services import pyatv_service
from home_automation_server.services.device_provider import DeviceCapability
from home_automation_server.services.samsungtv_service import SamsungTVProvider


class ProviderResolutionError(RuntimeError):
    """Raised when a provider cannot be built for the requested device."""


@dataclass
class AppleTVProvider:
    identifier: str
    ip_address: str
    credentials: dict[str, str]

    async def send_command(self, command: str) -> None:
        await pyatv_service.send_remote_command(
            self.identifier,
            self.ip_address,
            self.credentials,
            command,
        )

    async def power(self, turn_on: bool) -> None:
        await pyatv_service.power_toggle(
            self.identifier,
            self.ip_address,
            self.credentials,
            turn_on,
        )

    async def launch_app(self, app_id: str) -> None:
        await pyatv_service.launch_app(
            self.identifier,
            self.ip_address,
            self.credentials,
            app_id,
        )

    async def capabilities(self) -> set[DeviceCapability]:
        return {
            DeviceCapability.POWER,
            DeviceCapability.NAVIGATION,
            DeviceCapability.MEDIA,
            DeviceCapability.VOLUME,
            DeviceCapability.APP_LAUNCH,
            DeviceCapability.KEY_INPUT,
        }


@dataclass
class ResolvedProvider:
    provider: AppleTVProvider | SamsungTVProvider
    device_name: str


def resolve_provider(kind: DeviceKind, device_id: int, session: Session) -> ResolvedProvider:
    if kind == DeviceKind.APPLE_TV:
        device = session.get(AppleTVDevice, device_id)
        if not device:
            raise ProviderResolutionError("Apple TV device not found")

        pairings = session.exec(
            select(AppleTVPairing).where(AppleTVPairing.device_id == device_id)
        ).all()
        credentials = {p.protocol: p.credentials for p in pairings}

        if not credentials:
            raise ProviderResolutionError("No saved credentials for this device. Pair first.")

        provider = AppleTVProvider(
            identifier=device.identifier,
            ip_address=device.ip_address,
            credentials=credentials,
        )
        return ResolvedProvider(provider=provider, device_name=device.name)

    if kind == DeviceKind.SAMSUNG_TV:
        device = session.get(SamsungTVDevice, device_id)
        if not device:
            raise ProviderResolutionError("Samsung TV device not found")

        provider = SamsungTVProvider(
            ip_address=device.ip_address,
            model_year=device.model_year,
            name=device.name,
            port=device.port,
            token=device.token,
        )
        return ResolvedProvider(provider=provider, device_name=device.name)

    raise ProviderResolutionError(f"Unsupported device kind: {kind}")

