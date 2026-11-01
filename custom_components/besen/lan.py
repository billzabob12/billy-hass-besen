"""Share the LAN listener while entries or setup flows are using it."""

import asyncio
from dataclasses import dataclass, field
import time
from typing import Any, cast

from besen.udp import BesenUdpClient, BesenUdpHub

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN


class BesenTelemetryUdpClient(BesenUdpClient):
    """Stamp only live metering packets, never heartbeats or session summaries."""

    last_live_status: float | None = None

    def _update_charge_status(
        self, command: int, data: bytes, values: dict[str, Any]
    ) -> None:
        if command in (4, 13):
            self.last_live_status = time.monotonic()
        super()._update_charge_status(command, data, values)


@dataclass
class _UdpListener:
    hub: BesenUdpHub
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


@callback
def _async_listener(hass: HomeAssistant) -> _UdpListener:
    key = f"{DOMAIN}_udp"
    if key not in hass.data:
        listener = _UdpListener(hub=BesenUdpHub())
        hass.data[key] = listener

        async def stop_listener(event: Event) -> None:
            await listener.hub.async_stop()

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_listener)
    return cast(_UdpListener, hass.data[key])


async def async_acquire_udp_hub(hass: HomeAssistant) -> BesenUdpHub:
    """Acquire one use of the shared socket, including during setup."""
    listener = _async_listener(hass)
    async with listener.lock:
        await listener.hub.async_start()
        listener.users += 1
    return listener.hub


async def async_release_udp_hub(hass: HomeAssistant) -> None:
    """Close the listener after its final entry or setup flow releases it."""
    listener = _async_listener(hass)
    async with listener.lock:
        listener.users -= 1
        if listener.users == 0:
            await listener.hub.async_stop()
