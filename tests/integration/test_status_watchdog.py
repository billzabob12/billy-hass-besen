"""Verify read-only status probing and bounded session recovery."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from besen.udp import BesenUdpClient
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.besen.coordinator import BesenCoordinator
from custom_components.besen.lan import BesenTelemetryUdpClient

from .conftest import charger_state


def test_only_live_metering_packets_refresh_status_age():
    client = object.__new__(BesenTelemetryUdpClient)
    with (
        patch.object(BesenUdpClient, "_update_charge_status"),
        patch("custom_components.besen.lan.time.monotonic", return_value=123),
    ):
        client._update_charge_status(6, b"", {})
        assert client.last_live_status is None
        client._update_charge_status(13, b"", {})
        assert client.last_live_status == 123
        client._update_charge_status(6, b"", {})
        assert client.last_live_status == 123


@pytest.mark.parametrize("age", [0, 30, 91])
async def test_watchdog_never_issues_actuator_commands(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, age: int
):
    client = Mock(state=charger_state(), _send_command=AsyncMock())
    coordinator = BesenCoordinator(hass, mock_config_entry, client, uses_lan=True)
    coordinator._charge_health.received = 100 - age
    with (
        patch("custom_components.besen.status_health.time.monotonic", return_value=100),
        patch(
            "custom_components.besen.coordinator.asyncio.sleep",
            AsyncMock(side_effect=[None, asyncio.CancelledError()]),
        ),
        patch.object(coordinator, "async_pause_connection", AsyncMock()) as pause,
        patch.object(coordinator, "async_resume_connection", AsyncMock()) as resume,
    ):
        with pytest.raises(asyncio.CancelledError):
            await coordinator._async_watch_charge_status()
    if age == 0:
        client._send_command.assert_not_awaited()
        pause.assert_not_awaited()
    elif age == 30:
        assert [c.args[0] for c in client._send_command.await_args_list] == [
            0x800D,
            0x8006,
        ]
        pause.assert_not_awaited()
    else:
        pause.assert_awaited_once()
        resume.assert_awaited_once()
        client._send_command.assert_not_awaited()
