"""Unit tests for incident readiness gate state service."""

from backend.services.operations_state import OperationsState


async def test_incident_mode_blocks_resume_until_all_ready() -> None:
    """Incident mode should require all known stations to confirm ready."""
    state = OperationsState()

    await state.ensure_station("TK-01", "Trať 01")
    await state.ensure_station("ZT-05", "Zatáčka 05")
    await state.activate_incident_mode()

    allowed, missing = await state.can_resume()
    assert allowed is False
    assert missing == ["TK-01", "ZT-05"]

    await state.set_station_ready("TK-01", "Trať 01")
    allowed, missing = await state.can_resume()
    assert allowed is False
    assert missing == ["ZT-05"]

    await state.set_station_ready("ZT-05", "Zatáčka 05")
    allowed, missing = await state.can_resume()
    assert allowed is True
    assert missing == []


async def test_new_station_during_incident_starts_not_ready() -> None:
    """Station discovered while incident is active must not bypass gate."""
    state = OperationsState()

    await state.ensure_station("TK-01", "Trať 01")
    await state.activate_incident_mode()
    await state.ensure_station("NEW-11", "Nová stanice")

    allowed, missing = await state.can_resume()
    assert allowed is False
    assert missing == ["NEW-11", "TK-01"]
