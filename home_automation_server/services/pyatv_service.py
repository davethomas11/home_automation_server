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
import pyatv.exceptions as pyatv_exceptions
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

# Swipe direction → (start_x, start_y, end_x, end_y)
# Coordinates are in the range [0, 1000] as required by pyatv TouchGestures.
SWIPE_DIRECTION_MAP: dict[str, tuple[int, int, int, int]] = {
    "up":    (500, 750, 500, 250),
    "down":  (500, 250, 500, 750),
    "left":  (750, 500, 250, 500),
    "right": (250, 500, 750, 500),
}

# Remote command name → method name on RemoteControl interface
REMOTE_COMMAND_MAP: dict[str, str] = {
    # Navigation
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "select": "select",
    "menu": "menu",
    "home": "home",
    "home_hold": "home_hold",
    "top_menu": "top_menu",
    # Playback
    "play": "play",
    "pause": "pause",
    "play_pause": "play_pause",
    "stop": "stop",
    "next": "next",
    "previous": "previous",
    "skip_forward": "skip_forward",
    "skip_backward": "skip_backward",
    # Volume
    "volume_up": "volume_up",
    "volume_down": "volume_down",
    # Channels
    "channel_up": "channel_up",
    "channel_down": "channel_down",
    # System
    "screensaver": "screensaver",
    "control_center": "control_center",
    "wakeup": "wakeup",
    "suspend": "suspend",
    "guide": "guide",
    # Power (mapped via remote_control)
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
        try:
            app_list = await atv.apps.app_list()
        except pyatv_exceptions.NotSupportedError as exc:
            raise RuntimeError(
                "Installed app listing is not supported by this Apple TV/protocol. "
                "You can still launch an app manually by bundle ID."
            ) from exc
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
        # Power commands live on atv.power, not atv.remote_control.
        if method_name in ("turn_on", "turn_off"):
            power_method = getattr(atv.power, method_name)
            await power_method(await_new_state=True)
            logger.info("Sent power command '%s' to %s", command, identifier)
            return

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
    atv = await connect_to_device(identifier, ip_address, credentials)
    try:
        if turn_on:
            await atv.power.turn_on(await_new_state=True)
        else:
            await atv.power.turn_off(await_new_state=True)
        logger.info("Sent power_toggle turn_on=%s to %s", turn_on, identifier)
    finally:
        atv.close()


async def get_power_state(
    identifier: str,
    ip_address: str,
    credentials: dict[str, str],
) -> dict[str, object]:
    """Return current power state for the Apple TV."""
    atv = await connect_to_device(identifier, ip_address, credentials)
    try:
        try:
            state = atv.power.power_state
        except pyatv_exceptions.NotSupportedError as exc:
            raise RuntimeError(
                "Power state is not supported by this Apple TV/protocol."
            ) from exc

        state_name = str(state.name).lower()
        return {
            "state": state_name,
            "is_on": state_name == "on",
        }
    finally:
        atv.close()


# ---------------------------------------------------------------------------
# Swipe gestures
# ---------------------------------------------------------------------------

async def swipe_gesture(
    identifier: str,
    ip_address: str,
    credentials: dict[str, str],
    direction: str | None = None,
    start_x: int | None = None,
    start_y: int | None = None,
    end_x: int | None = None,
    end_y: int | None = None,
    duration_ms: int = 300,
) -> None:
    """
    Perform a swipe gesture on the Apple TV touchpad.

    You can either supply a named *direction* (``"up"``, ``"down"``,
    ``"left"``, ``"right"``) which maps to preset coordinates, **or** provide
    explicit ``start_x``, ``start_y``, ``end_x``, ``end_y`` values
    (each in the range 0–1000).

    ``duration_ms`` controls how long the swipe takes (default 300 ms).
    """
    if direction is not None:
        coords = SWIPE_DIRECTION_MAP.get(direction.lower())
        if coords is None:
            raise ValueError(
                f"Unknown swipe direction: '{direction}'. "
                f"Choose from {list(SWIPE_DIRECTION_MAP)} or supply explicit coordinates."
            )
        sx, sy, ex, ey = coords
    else:
        if None in (start_x, start_y, end_x, end_y):
            raise ValueError(
                "Provide either 'direction' or all of 'start_x', 'start_y', 'end_x', 'end_y'."
            )
        sx, sy, ex, ey = int(start_x), int(start_y), int(end_x), int(end_y)  # type: ignore[arg-type]

    atv = await connect_to_device(identifier, ip_address, credentials)
    try:
        handler = getattr(atv, 'touch_gestures', None) or getattr(atv, 'remote_control', None)

        if handler is None or not hasattr(handler, 'swipe'):
            raise RuntimeError(
                f"Device {identifier} does not support swipe gestures via any available interface."
            )

        try:
            await handler.swipe(sx, sy, ex, ey, int(duration_ms))
        except pyatv_exceptions.NotSupportedError as exc:
            raise RuntimeError(
                "Swipe gestures are not supported by this Apple TV/protocol."
            ) from exc

        logger.info(
            "Swipe gesture (%s→%s, %s→%s) over %s ms sent to %s",
            sx, ex, sy, ey, duration_ms, identifier,
        )
    except Exception:
        logger.error(
            "Failed to perform swipe gesture (%s→%s, %s→%s) on %s",
            sx, ex, sy, ey, identifier,
            exc_info=True,
        )
        raise
    finally:
        atv.close()


