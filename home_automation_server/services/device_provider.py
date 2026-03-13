"""Provider abstractions for multi-device control backends."""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class DeviceCapability(str, Enum):
    POWER = "power"
    VOLUME = "volume"
    NAVIGATION = "navigation"
    MEDIA = "media"
    APP_LAUNCH = "app_launch"
    KEY_INPUT = "key_input"


class DeviceProvider(Protocol):
    async def send_command(self, command: str) -> None:
        """Send a normalized command string to the device."""

    async def power(self, turn_on: bool) -> None:
        """Toggle device power state."""

    async def launch_app(self, app_id: str) -> None:
        """Launch an app by provider-specific app identifier."""

    async def capabilities(self) -> set[DeviceCapability]:
        """Return supported capabilities for this provider instance."""

