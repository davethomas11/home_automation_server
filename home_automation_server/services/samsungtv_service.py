"""Samsung TV service wrapper with backend selection by model year."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

from home_automation_server.services.device_provider import DeviceCapability

logger = logging.getLogger(__name__)


class SamsungTVError(RuntimeError):
    """Raised when Samsung TV command execution fails."""


class SamsungTVKey(str, Enum):
    # Power
    HOME = "home"
    POWER_OFF = "power_off"
    # Navigation
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    SELECT = "select"
    BACK = "back"
    # System
    SOURCE = "source"
    SETTINGS = "settings"
    INFO = "info"
    MENU = "menu"
    GUIDE = "guide"
    # Volume / Channel
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    MUTE = "mute"
    UNMUTE = "unmute"
    CHANNEL_UP = "channel_up"
    CHANNEL_DOWN = "channel_down"
    # Playback
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    REWIND = "rewind"
    FAST_FORWARD = "fast_forward"
    PREVIOUS = "previous"
    NEXT = "next"
    # Number pad
    NUM_0 = "num_0"
    NUM_1 = "num_1"
    NUM_2 = "num_2"
    NUM_3 = "num_3"
    NUM_4 = "num_4"
    NUM_5 = "num_5"
    NUM_6 = "num_6"
    NUM_7 = "num_7"
    NUM_8 = "num_8"
    NUM_9 = "num_9"
    # Colour / function buttons
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    # Picture / Sound
    PICTURE_MODE = "picture_mode"
    SOUND_MODE = "sound_mode"
    # SmartHub / Apps
    SMART_HUB = "smart_hub"
    # Direct input switching
    # NOTE: KEY_HDMI1-4 are NOT reliably supported on Tizen (2016+) Samsung TVs via the
    # local WebSocket API. KEY_HDMI cycles through HDMI inputs; KEY_SOURCE opens the
    # on-screen picker. Direct named-input switching requires the SmartThings cloud API.
    HDMI_CYCLE = "hdmi_cycle"
    HDMI_1 = "hdmi_1"
    HDMI_2 = "hdmi_2"
    HDMI_3 = "hdmi_3"
    HDMI_4 = "hdmi_4"
    AV_1 = "av_1"
    COMPONENT_1 = "component_1"
    PC = "pc"
    EXTERNAL = "external"


KEY_TO_REMOTE: dict[SamsungTVKey, str] = {
    # Power
    SamsungTVKey.HOME:          "KEY_HOME",
    SamsungTVKey.POWER_OFF:     "KEY_POWEROFF",
    # Navigation
    SamsungTVKey.UP:            "KEY_UP",
    SamsungTVKey.DOWN:          "KEY_DOWN",
    SamsungTVKey.LEFT:          "KEY_LEFT",
    SamsungTVKey.RIGHT:         "KEY_RIGHT",
    SamsungTVKey.SELECT:        "KEY_ENTER",
    SamsungTVKey.BACK:          "KEY_RETURN",
    # System
    SamsungTVKey.SOURCE:        "KEY_SOURCE",
    SamsungTVKey.SETTINGS:      "KEY_MENU",
    SamsungTVKey.INFO:          "KEY_INFO",
    SamsungTVKey.MENU:          "KEY_MENU",
    SamsungTVKey.GUIDE:         "KEY_GUIDE",
    # Volume / Channel
    SamsungTVKey.VOLUME_UP:     "KEY_VOLUP",
    SamsungTVKey.VOLUME_DOWN:   "KEY_VOLDOWN",
    SamsungTVKey.MUTE:          "KEY_MUTE",
    SamsungTVKey.UNMUTE:        "KEY_MUTE",
    SamsungTVKey.CHANNEL_UP:    "KEY_CHUP",
    SamsungTVKey.CHANNEL_DOWN:  "KEY_CHDOWN",
    # Playback
    SamsungTVKey.PLAY:          "KEY_PLAY",
    SamsungTVKey.PAUSE:         "KEY_PAUSE",
    SamsungTVKey.STOP:          "KEY_STOP",
    SamsungTVKey.REWIND:        "KEY_REWIND",
    SamsungTVKey.FAST_FORWARD:  "KEY_FF",
    SamsungTVKey.PREVIOUS:      "KEY_REWIND",
    SamsungTVKey.NEXT:          "KEY_FF",
    # Number pad
    SamsungTVKey.NUM_0:         "KEY_0",
    SamsungTVKey.NUM_1:         "KEY_1",
    SamsungTVKey.NUM_2:         "KEY_2",
    SamsungTVKey.NUM_3:         "KEY_3",
    SamsungTVKey.NUM_4:         "KEY_4",
    SamsungTVKey.NUM_5:         "KEY_5",
    SamsungTVKey.NUM_6:         "KEY_6",
    SamsungTVKey.NUM_7:         "KEY_7",
    SamsungTVKey.NUM_8:         "KEY_8",
    SamsungTVKey.NUM_9:         "KEY_9",
    # Colour / function buttons
    SamsungTVKey.RED:           "KEY_RED",
    SamsungTVKey.GREEN:         "KEY_GREEN",
    SamsungTVKey.YELLOW:        "KEY_YELLOW",
    SamsungTVKey.BLUE:          "KEY_BLUE",
    # Picture / Sound
    SamsungTVKey.PICTURE_MODE:  "KEY_PICTUREMODE",
    SamsungTVKey.SOUND_MODE:    "KEY_SOUNDMODE",
    # SmartHub
    SamsungTVKey.SMART_HUB:     "KEY_SMARTHUB",
    # Direct input switching
    # KEY_HDMI cycles through HDMI ports — the most reliable local-API input command.
    # KEY_HDMI1-4 / KEY_AV1 / KEY_COMPONENT1 / KEY_PC are sent as-is but are only
    # honoured by a subset of older Samsung models; Tizen 2016+ typically ignores them.
    SamsungTVKey.HDMI_CYCLE:    "KEY_HDMI",
    SamsungTVKey.HDMI_1:        "KEY_HDMI1",
    SamsungTVKey.HDMI_2:        "KEY_HDMI2",
    SamsungTVKey.HDMI_3:        "KEY_HDMI3",
    SamsungTVKey.HDMI_4:        "KEY_HDMI4",
    SamsungTVKey.AV_1:          "KEY_AV1",
    SamsungTVKey.COMPONENT_1:   "KEY_COMPONENT1",
    SamsungTVKey.PC:            "KEY_PC",
    SamsungTVKey.EXTERNAL:      "KEY_EXTERNAL",
}


class SamsungTVProvider:
    """
    Unified Samsung TV provider.

    - 2016-2023 defaults to samsungtvws
    - 2024+ defaults to py-samsungtv

    This class is intentionally conservative in Phase 1: it focuses on API shape,
    backend selection, and robust error handling. Command coverage can be expanded
    in Phase 2 as device-specific behavior is validated.
    """

    def __init__(
        self,
        *,
        ip_address: str,
        model_year: int,
        name: str,
        port: int = 8002,
        token: str | None = None,
    ) -> None:
        self.ip_address = ip_address
        self.model_year = model_year
        self.name = name
        self.port = port
        self.token = token
        self.backend = "py_samsungtv" if model_year >= 2024 else "samsungtvws"

    async def capabilities(self) -> set[DeviceCapability]:
        return {
            DeviceCapability.POWER,
            DeviceCapability.VOLUME,
            DeviceCapability.NAVIGATION,
            DeviceCapability.MEDIA,
            DeviceCapability.APP_LAUNCH,
            DeviceCapability.KEY_INPUT,
        }

    async def send_command(self, command: str) -> None:
        try:
            key = SamsungTVKey(command)
        except ValueError as exc:
            supported = ", ".join(sorted(k.value for k in SamsungTVKey))
            raise SamsungTVError(f"Unsupported Samsung command '{command}'. Supported: {supported}") from exc

        remote_key = KEY_TO_REMOTE[key]
        await self.send_key(remote_key)

    async def power(self, turn_on: bool) -> None:
        if turn_on:
            await self.power_on()
        else:
            await self.power_off()

    async def power_on(self) -> None:
        logger.info("Power on requested for Samsung TV '%s' (%s)", self.name, self.ip_address)
        # Phase 1 placeholder:
        # LAN power-on can require WoL or external integrations depending on model/network.
        raise SamsungTVError("Power on is not yet implemented for Samsung TVs in Phase 1.")

    async def power_off(self) -> None:
        await self.send_key("KEY_POWEROFF")

    async def volume_up(self) -> None:
        await self.send_key("KEY_VOLUP")

    async def volume_down(self) -> None:
        await self.send_key("KEY_VOLDOWN")

    async def mute(self) -> None:
        await self.send_key("KEY_MUTE")

    async def unmute(self) -> None:
        await self.send_key("KEY_MUTE")

    async def home(self) -> None:
        await self.send_key("KEY_HOME")

    async def back(self) -> None:
        await self.send_key("KEY_RETURN")

    async def play(self) -> None:
        await self.send_key("KEY_PLAY")

    async def pause(self) -> None:
        await self.send_key("KEY_PAUSE")

    async def launch_app(self, app_id: str) -> None:
        try:
            if self.backend == "samsungtvws":
                await self._launch_app_samsungtvws(app_id)
            else:
                await self._launch_app_py_samsungtv(app_id)
        except Exception as exc:  # pragma: no cover - depends on optional backend libs
            logger.exception("Failed launching app %s on Samsung TV %s", app_id, self.ip_address)
            raise SamsungTVError(f"Failed to launch app '{app_id}' on Samsung TV: {exc}") from exc

    async def send_key(self, key: str) -> None:
        try:
            if self.backend == "samsungtvws":
                await self._send_key_samsungtvws(key)
            else:
                await self._send_key_py_samsungtv(key)
        except Exception as exc:  # pragma: no cover - depends on optional backend libs
            logger.exception("Failed sending key %s to Samsung TV %s", key, self.ip_address)
            raise SamsungTVError(f"Failed to send key '{key}' to Samsung TV: {exc}") from exc

    async def _send_key_samsungtvws(self, key: str) -> None:
        try:
            from samsungtvws import SamsungTVWS
        except Exception as exc:  # pragma: no cover
            raise SamsungTVError("samsungtvws is not installed. Add it to project dependencies.") from exc

        def _send() -> None:
            remote = SamsungTVWS(host=self.ip_address, port=self.port, token=self.token)
            remote.send_key(key)

        await asyncio.to_thread(_send)

    async def _launch_app_samsungtvws(self, app_id: str) -> None:
        try:
            from samsungtvws import SamsungTVWS
        except Exception as exc:  # pragma: no cover
            raise SamsungTVError("samsungtvws is not installed. Add it to project dependencies.") from exc

        def _launch() -> None:
            remote = SamsungTVWS(host=self.ip_address, port=self.port, token=self.token)
            remote.run_app(app_id)

        await asyncio.to_thread(_launch)

    async def _send_key_py_samsungtv(self, key: str) -> None:
        try:
            from samsungtv import SamsungTVAsyncRemote
        except Exception as exc:  # pragma: no cover
            raise SamsungTVError("py-samsungtv is not installed. Add it to project dependencies.") from exc

        async with SamsungTVAsyncRemote(host=self.ip_address, port=self.port) as remote:
            await remote.send_key(key)

    async def _launch_app_py_samsungtv(self, app_id: str) -> None:
        try:
            from samsungtv import SamsungTVAsyncRemote
        except Exception as exc:  # pragma: no cover
            raise SamsungTVError("py-samsungtv is not installed. Add it to project dependencies.") from exc

        async with SamsungTVAsyncRemote(host=self.ip_address, port=self.port) as remote:
            await remote.run_app(app_id)


@dataclass
class DiscoveredSamsungDevice:
    name: str
    ip_address: str
    model: str | None = None
    model_year: int | None = None
    port: int = 8002


def _parse_discovered_item(item: object) -> DiscoveredSamsungDevice | None:
    if isinstance(item, str):
        return DiscoveredSamsungDevice(name=f"Samsung TV ({item})", ip_address=item)

    if not isinstance(item, dict):
        return None

    ip_address = (
        item.get("ip")
        or item.get("ip_address")
        or item.get("host")
        or item.get("address")
    )
    if not ip_address:
        return None

    model = item.get("model") or item.get("model_name") or item.get("device_type")
    name = item.get("name") or item.get("friendly_name") or item.get("device_name")
    if not name:
        name = f"Samsung TV ({ip_address})"

    model_year_raw = item.get("model_year") or item.get("year")
    model_year: int | None = None
    if model_year_raw is not None:
        try:
            model_year = int(model_year_raw)
        except (TypeError, ValueError):
            model_year = None

    port_raw = item.get("port", 8002)
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 8002

    return DiscoveredSamsungDevice(
        name=str(name),
        ip_address=str(ip_address),
        model=str(model) if model is not None else None,
        model_year=model_year,
        port=port,
    )


def _discover_with_samsungtvws(timeout: float) -> list[object]:
    try:
        from samsungtvws import SamsungTVWS
    except Exception as exc:  # pragma: no cover
        raise SamsungTVError("samsungtvws is not installed. Add it to project dependencies.") from exc

    discover_method = getattr(SamsungTVWS, "discover", None)
    if callable(discover_method):
        try:
            result = discover_method(timeout=timeout)
        except TypeError:
            result = discover_method()
        return list(result or [])

    try:
        from samsungtvws import discover as module_discover
    except Exception as exc:
        raise SamsungTVError(
            "samsungtvws discovery API is unavailable in this installed version. "
            "Try upgrading samsungtvws."
        ) from exc

    try:
        result = module_discover(timeout=timeout)
    except TypeError:
        result = module_discover()
    return list(result or [])


def _discover_via_ping_sweep(common_subnets: list[str] | None = None) -> list[object]:
    """
    Fallback: try to connect to common Samsung TV IPs on port 8002 (non-intrusive check).
    
    For older samsungtvws versions without discovery API, this attempts connection to
    common home network subnets (192.168.x.x, 10.0.x.x) to find active TVs.
    
    This is slow but works as last resort.
    """
    if common_subnets is None:
        common_subnets = [
            "192.168.1",
            "192.168.0",
            "10.0.0",
            "172.16.0",
        ]
    
    found: list[object] = []
    
    try:
        from samsungtvws import SamsungTVWS
    except Exception:
        return []
    
    import socket
    
    for subnet in common_subnets:
        for i in range(1, 50):
            ip = f"{subnet}.{i}"
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                result = sock.connect_ex((ip, 8002))
                sock.close()
                if result == 0:
                    try:
                        tv = SamsungTVWS(host=ip, port=8002)
                        if hasattr(tv, 'close'):
                            tv.close()
                        found.append({"ip_address": ip, "port": 8002})
                        logger.info("Found Samsung TV at %s", ip)
                    except Exception:
                        logger.debug("Connection test to %s:8002 succeeded but TV init failed: %s", ip, e)
                        pass
            except Exception:
                pass
    
    return found


async def scan_for_samsung_devices(timeout: float = 4.0) -> list[DiscoveredSamsungDevice]:
    """Scan local network for Samsung TVs."""


async def scan_for_samsung_devices_with_airplay(
    airplay_devices: list[dict] | None = None,
    timeout: float = 4.0,
) -> list[DiscoveredSamsungDevice]:
    """
    Scan for Samsung TVs, optionally using AirPlay-discovered devices to find Samsung TV IPs.
    
    Args:
        airplay_devices: Optional list of AirPlay-discovered devices with IP addresses.
                        If provided, will attempt to connect to these IPs as Samsung TVs first.
        timeout: Timeout for discovery operations.
    
    Returns:
        List of discovered Samsung TV devices.
    """
    found: list[DiscoveredSamsungDevice] = []
    seen_ips: set[str] = set()

    # First, try AirPlay devices that look like Samsung TVs
    if airplay_devices:
        try:
            from samsungtvws import SamsungTVWS
        except Exception:
            pass
        else:
            for device in airplay_devices:
                ip = device.get("ip_address") or device.get("address")
                name = device.get("name", "Samsung TV")
                if not ip or ip in seen_ips:
                    continue

                # Quick test: try to connect as Samsung TV
                try:
                    import socket

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    result = sock.connect_ex((ip, 8002))
                    sock.close()

                    if result == 0:
                        parsed = DiscoveredSamsungDevice(
                            name=str(name),
                            ip_address=str(ip),
                            model=None,
                            model_year=None,
                            port=8002,
                        )
                        found.append(parsed)
                        seen_ips.add(ip)
                        logger.info("Found Samsung TV via AirPlay discovery at %s", ip)
                except Exception:
                    pass

    # Then try primary discovery API
    try:
        discovered = await asyncio.to_thread(_discover_with_samsungtvws, timeout)
    except SamsungTVError:
        logger.warning("Primary discovery API unavailable.")
        discovered = []
    except Exception as exc:  # pragma: no cover - library-specific behavior
        logger.exception("Failed to scan for Samsung TVs")
        raise SamsungTVError(f"Failed to scan for Samsung TVs: {exc}") from exc

    # Parse discovered devices and avoid duplicates
    parsed: list[DiscoveredSamsungDevice] = []
    for item in discovered:
        parsed_item = _parse_discovered_item(item)
        if parsed_item is None:
            continue
        if parsed_item.ip_address in seen_ips:
            continue
        seen_ips.add(parsed_item.ip_address)
        parsed.append(parsed_item)

    found.extend(parsed)
    logger.info("Discovered %s Samsung TV device(s)", len(parsed))
    return found


async def scan_for_samsung_devices(timeout: float = 4.0) -> list[DiscoveredSamsungDevice]:
    """Scan local network for Samsung TVs using primary discovery API."""
    return await scan_for_samsung_devices_with_airplay(airplay_devices=None, timeout=timeout)


async def pair_samsung_device(ip_address: str, port: int = 8002, token: str | None = None) -> str | None:
    """
    Attempt to pair/authenticate with a Samsung TV and return token if available.

    Notes:
    - On many Samsung TVs, pairing occurs on first command and requires confirming a prompt.
    - This helper sends a lightweight HOME key as handshake.
    """
    try:
        from samsungtvws import SamsungTVWS
    except Exception as exc:  # pragma: no cover
        raise SamsungTVError("samsungtvws is not installed. Add it to project dependencies.") from exc

    def _pair() -> str | None:
        remote = SamsungTVWS(host=ip_address, port=port, token=token)
        remote.send_key("KEY_HOME")
        return getattr(remote, "token", None) or token

    try:
        return await asyncio.to_thread(_pair)
    except Exception as exc:  # pragma: no cover - depends on TV/library behavior
        logger.exception("Failed Samsung TV pairing handshake with %s", ip_address)
        raise SamsungTVError(f"Failed to pair/authenticate with Samsung TV: {exc}") from exc


