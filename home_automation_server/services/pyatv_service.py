"""
pyatv service wrapper.

Provides async helpers for:
- Scanning for Apple TVs on the local network
- Initiating and completing pairing for MRP, Companion, and AirPlay protocols
- Connecting to a device using saved credentials
- Launching apps by bundle ID
- Sending remote control commands
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import pyatv
import pyatv.const as const
from pyatv.interface import AppleTV, PairingHandler

from home_automation_server.core.config import settings

logger = logging.getLogger(__name__)

# Protocol name → pyatv Protocol enum
PROTOCOL_MAP: dict[str, const.Protocol] = {
    "MRP": const.Protocol.MRP,
    "Companion": const.Protocol.Companion,
    "AirPlay": const.Protocol.AirPlay,
    "DMAP": const.Protocol.DMAP,
    "RAOP": const.Protocol.RAOP,
}

# Remote command name → method name on RemoteControl interface
REMOTE_COMMAND_MAP: dict[str, str] = {
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "select": "select",
    "menu": "menu",
    "home": "home",
    "play": "play",
    "pause": "pause",
    "play_pause": "play_pause",
    "stop": "stop",
    "next": "next",
    "previous": "previous",
    "volume_up": "volume_up",
    "volume_down": "volume_down",
    "turn_on": "turn_on",
    "turn_off": "turn_off",
}


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

@dataclass
class DiscoveredDevice:
    name: str
    identifier: str
    ip_address: str
    model: str
    os_version: str


async def scan_for_devices(timeout: float | None = None) -> list[DiscoveredDevice]:
    """Scan the local network and return discovered Apple TV devices."""
    timeout = timeout or settings.scan_timeout
    loop = asyncio.get_event_loop()
    found = await pyatv.scan(loop=loop, timeout=timeout)

    results: list[DiscoveredDevice] = []
    for atv in found:
        address = str(atv.address)
        identifier = atv.identifier or address
        results.append(
            DiscoveredDevice(
                name=atv.name,
                identifier=identifier,
                ip_address=address,
                model=str(atv.device_info.model) if atv.device_info else "Unknown",
                os_version=str(atv.device_info.version) if atv.device_info else "Unknown",
            )
        )
        logger.info("Discovered: %s (%s) at %s", atv.name, identifier, address)

    return results


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------

# In-memory store for active pairing handlers (keyed by identifier+protocol)
_active_pairings: dict[str, PairingHandler] = {}


def _pairing_key(identifier: str, protocol: str) -> str:
    return f"{identifier}:{protocol}"


async def start_pairing(identifier: str, ip_address: str, protocol_name: str) -> str:
    """
    Begin the pairing flow for the given device and protocol.
    Returns a status message. The caller must then call finish_pairing() with the PIN.
    """
    protocol = PROTOCOL_MAP.get(protocol_name)
    if protocol is None:
        raise ValueError(f"Unknown protocol: {protocol_name}. Choose from {list(PROTOCOL_MAP)}")

    loop = asyncio.get_event_loop()
    found = await pyatv.scan(loop=loop, identifier=identifier, timeout=settings.scan_timeout)
    if not found:
        raise RuntimeError(f"Device {identifier} not found on network.")

    atv_conf = found[0]
    pairing = await pyatv.pair(atv_conf, protocol=protocol, loop=loop)
    await pairing.begin()

    key = _pairing_key(identifier, protocol_name)
    _active_pairings[key] = pairing

    if pairing.device_provides_pin:
        return "PIN displayed on device – call finish_pairing with that PIN."
    else:
        return "Enter any PIN in the app and provide it to the device when prompted."


async def finish_pairing(identifier: str, protocol_name: str, pin: str) -> str:
    """
    Submit the PIN and finalise pairing. Returns the serialised credentials string.
    """
    key = _pairing_key(identifier, protocol_name)
    pairing = _active_pairings.get(key)
    if pairing is None:
        raise RuntimeError("No active pairing session found. Call start_pairing first.")

    pairing.pin(pin)
    await pairing.finish()

    if not pairing.has_paired:
        await pairing.close()
        del _active_pairings[key]
        raise RuntimeError("Pairing failed – incorrect PIN or timeout.")

    credentials = str(pairing.service.credentials)
    await pairing.close()
    del _active_pairings[key]

    logger.info("Pairing successful for %s / %s", identifier, protocol_name)
    return credentials


# ---------------------------------------------------------------------------
# Connecting
# ---------------------------------------------------------------------------

async def connect_to_device(
    identifier: str,
    ip_address: str,
    credentials: dict[str, str],  # protocol_name → credential_string
) -> AppleTV:
    """
    Scan for device, apply stored credentials, and return a connected AppleTV instance.
    Caller is responsible for calling atv.close() when done.
    """
    loop = asyncio.get_event_loop()
    found = await pyatv.scan(loop=loop, identifier=identifier, timeout=settings.scan_timeout)
    if not found:
        raise RuntimeError(f"Device {identifier} not found on network.")

    atv_conf = found[0]

    for protocol_name, cred_string in credentials.items():
        protocol = PROTOCOL_MAP.get(protocol_name)
        if protocol and cred_string:
            atv_conf.set_credentials(protocol, cred_string)

    atv = await pyatv.connect(atv_conf, loop=loop)
    logger.info("Connected to %s", identifier)
    return atv


# ---------------------------------------------------------------------------
# App launching
# ---------------------------------------------------------------------------

async def launch_app(
    identifier: str,
    ip_address: str,
    credentials: dict[str, str],
    bundle_id: str,
) -> None:
    """Launch an app on the Apple TV by bundle ID."""
    atv = await connect_to_device(identifier, ip_address, credentials)
    try:
        await atv.apps.launch_app(bundle_id)
        logger.info("Launched app %s on %s", bundle_id, identifier)
    finally:
        atv.close()


async def list_apps(
    identifier: str,
    ip_address: str,
    credentials: dict[str, str],
) -> list[dict[str, str]]:
    """Return installed apps on the Apple TV."""
    atv = await connect_to_device(identifier, ip_address, credentials)
    try:
        app_list = await atv.apps.app_list()
        return [{"name": a.name, "bundle_id": a.identifier} for a in app_list]
    finally:
        atv.close()


# ---------------------------------------------------------------------------
# Remote commands
# ---------------------------------------------------------------------------

async def send_remote_command(
    identifier: str,
    ip_address: str,
    credentials: dict[str, str],
    command: str,
) -> None:
    """Send a remote control command to the Apple TV."""
    method_name = REMOTE_COMMAND_MAP.get(command)
    if method_name is None:
        raise ValueError(f"Unknown command: {command}. Choose from {list(REMOTE_COMMAND_MAP)}")

    atv = await connect_to_device(identifier, ip_address, credentials)
    try:
        rc = atv.remote_control
        method = getattr(rc, method_name)
        await method()
        logger.info("Sent command '%s' to %s", command, identifier)
    finally:
        atv.close()


# ---------------------------------------------------------------------------
# Power
# ---------------------------------------------------------------------------

async def power_toggle(
    identifier: str,
    ip_address: str,
    credentials: dict[str, str],
    turn_on: bool,
) -> None:
    """Turn the Apple TV on or off."""
    command = "turn_on" if turn_on else "turn_off"
    await send_remote_command(identifier, ip_address, credentials, command)

