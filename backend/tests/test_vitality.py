"""Unit tests for station vitality monitoring."""

import asyncio

import pytest

from backend.services.vitality import VitalityMonitor


@pytest.mark.asyncio
async def test_station_goes_offline_after_disconnect() -> None:
    """Station should be marked offline when its last connection disconnects."""
    monitor = VitalityMonitor(check_interval_seconds=60, offline_timeout_seconds=120)

    await monitor.mark_seen(
        connection_id="1234",
        station_id="TK-01",
        name="Komisar 1",
        role="komisar_trat",
    )

    await monitor.mark_disconnected("1234")
    statuses = await monitor.get_station_statuses()

    assert len(statuses) == 1
    assert statuses[0]["station_id"] == "TK-01"
    assert statuses[0]["online"] is False


@pytest.mark.asyncio
async def test_station_times_out_without_heartbeat() -> None:
    """Station should become offline after timeout without new activity."""
    monitor = VitalityMonitor(check_interval_seconds=60, offline_timeout_seconds=1)

    await monitor.mark_seen(
        connection_id="5678",
        station_id="TK-02",
        name="Komisar 2",
        role="komisar_trat",
    )

    await asyncio.sleep(1.2)
    await monitor.run_timeout_check()
    statuses = await monitor.get_station_statuses()

    assert len(statuses) == 1
    assert statuses[0]["station_id"] == "TK-02"
    assert statuses[0]["online"] is False
