"""WebSocket API endpoint and message processing pipeline."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.auth import auth_manager
from backend.core.connection_manager import connection_manager
from backend.core.event_logger import event_logger
from backend.models.message import MessagePriority, MessageType, StationMessage
from backend.services.operations_state import operations_state
from backend.services.vitality import vitality_monitor

router = APIRouter(tags=["websocket"])


async def _resolve_user(auth_identifier: str) -> dict[str, Any] | None:
    """Resolve PIN/session identifier to normalized user payload.

    Args:
        auth_identifier: PIN code or session token.

    Returns:
        Normalized user data used by WebSocket pipeline, or None when invalid.
    """
    komisar = auth_manager.verify_pin(auth_identifier)
    if komisar:
        return {
            "name": komisar.name,
            "role": komisar.role.value,
            "station_id": komisar.station_id,
            "auth_id": auth_identifier,
            "phone": komisar.phone,
        }

    session_data = auth_manager.verify_session(auth_identifier)
    if session_data:
        return {
            "name": session_data["name"],
            "role": session_data["role"].value,
            "station_id": None,
            "auth_id": auth_identifier,
            "phone": session_data.get("phone"),
        }

    return None


async def _send_welcome_message(websocket: WebSocket, user_data: dict[str, Any]) -> None:
    """Send welcome system event after successful connection.

    Args:
        websocket: Accepted WebSocket connection.
        user_data: Normalized authenticated user payload.
    """
    welcome_payload = {
        "type": "system",
        "message": f"V\u00edtejte, {user_data['name']}! P\u0159ipojeno.",
        "timestamp": datetime.utcnow().isoformat(),
        "active_users": connection_manager.get_active_count(),
    }
    await websocket.send_text(json.dumps(welcome_payload, ensure_ascii=False))


async def _register_user_connection(websocket: WebSocket, user_data: dict[str, Any]) -> None:
    """Register authenticated user in connection/vitality state stores.

    Args:
        websocket: Incoming WebSocket connection.
        user_data: Normalized authenticated user payload.
    """
    await connection_manager.connect(
        websocket=websocket,
        pin_code=user_data["auth_id"],
        name=user_data["name"],
        role=user_data["role"],
        station_id=user_data["station_id"],
    )
    await vitality_monitor.mark_seen(
        connection_id=user_data["auth_id"],
        station_id=user_data["station_id"],
        name=user_data["name"],
        role=user_data["role"],
    )
    await operations_state.ensure_station(user_data["station_id"], user_data["name"])


async def _handle_resume_gate(
    websocket: WebSocket,
    station_message: StationMessage,
    user_data: dict[str, Any],
    message_data: dict[str, Any],
) -> tuple[bool, list[str], bool]:
    """Evaluate RZ resume gate and publish related notices.

    Args:
        websocket: Sender connection.
        station_message: Parsed message payload.
        user_data: Authenticated sender data.
        message_data: Raw JSON message body from client.

    Returns:
        Tuple ``(resume_with_warnings, missing_stations, should_continue)``.
    """
    resume_with_warnings = False
    resume_missing_stations: list[str] = []

    if station_message.operation_command != "rz_resume":
        return resume_with_warnings, resume_missing_stations, False

    can_resume, missing_stations = await operations_state.can_resume()
    force_resume = bool(message_data.get("force_resume", False))

    if not can_resume and not force_resume:
        blocked_payload = {
            "type": "error",
            "message": "RZ nelze obnovit: chyb\u00ed READY potvrzen\u00ed.",
            "details": {
                "missing_stations": missing_stations,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        await websocket.send_text(json.dumps(blocked_payload, ensure_ascii=False))

        gate_notice = {
            "message_id": f"gate_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "sender": {
                "user_id": "system",
                "name": "Syst\u00e9m",
                "role": "system",
                "phone": None,
            },
            "message_type": MessageType.SYSTEM.value,
            "priority": MessagePriority.HIGH.value,
            "content": (
                "\u26d4 RZ nelze obnovit. Chyb\u00ed READY potvrzen\u00ed: "
                f"{', '.join(missing_stations) if missing_stations else 'N/A'}"
            ),
            "created_at": datetime.utcnow().isoformat(),
        }
        await connection_manager.broadcast_to_roles(
            json.dumps(gate_notice, ensure_ascii=False),
            ["vedouci", "zastupce"],
        )
        event_logger.log_event(
            "operation_action",
            {
                "command": "rz_resume",
                "result": "blocked_missing_ready",
                "actor": user_data["name"],
                "role": user_data["role"],
                "missing_stations": missing_stations,
            },
            severity="warning",
        )
        return resume_with_warnings, resume_missing_stations, True

    if not can_resume and force_resume:
        resume_with_warnings = True
        resume_missing_stations = missing_stations
        override_notice = {
            "message_id": f"gate_override_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "sender": {
                "user_id": "system",
                "name": "Syst\u00e9m",
                "role": "system",
                "phone": None,
            },
            "message_type": MessageType.SYSTEM.value,
            "priority": MessagePriority.HIGH.value,
            "content": (
                "\u26a0\ufe0f RZ spu\u0161t\u011bna i p\u0159es warning. Chyb\u011bj\u00edc\u00ed READY: "
                f"{', '.join(missing_stations) if missing_stations else 'N/A'}"
            ),
            "created_at": datetime.utcnow().isoformat(),
        }
        await connection_manager.broadcast_to_roles(
            json.dumps(override_notice, ensure_ascii=False),
            ["vedouci", "zastupce"],
        )
        event_logger.log_event(
            "operation_action",
            {
                "command": "rz_resume",
                "result": "forced_with_warnings",
                "actor": user_data["name"],
                "role": user_data["role"],
                "missing_stations": missing_stations,
            },
            severity="warning",
        )

    if can_resume:
        event_logger.log_event(
            "operation_action",
            {
                "command": "rz_resume",
                "result": "normal",
                "actor": user_data["name"],
                "role": user_data["role"],
            },
        )

    await operations_state.resolve_incident_mode()
    return resume_with_warnings, resume_missing_stations, False


async def _process_message(
    websocket: WebSocket,
    user_data: dict[str, Any],
    data: str,
) -> None:
    """Process one incoming raw WebSocket message.

    Args:
        websocket: Sender connection.
        user_data: Authenticated sender data.
        data: Raw text payload.
    """
    try:
        message_data = json.loads(data)

        station_message = StationMessage(
            message_id=f"msg_{datetime.utcnow().timestamp()}",
            sender_pin=user_data["auth_id"],
            sender_name=user_data["name"],
            message_type=message_data.get("message_type", "chat"),
            priority=message_data.get("priority", "normal"),
            content=message_data.get("content", ""),
            target_roles=message_data.get("target_roles"),
            operation_command=message_data.get("operation_command"),
            readiness_state=message_data.get("readiness_state"),
        )

        await vitality_monitor.mark_seen(
            connection_id=user_data["auth_id"],
            station_id=user_data["station_id"],
            name=user_data["name"],
            role=user_data["role"],
        )
        await operations_state.ensure_station(user_data["station_id"], user_data["name"])

        if station_message.readiness_state == "ready":
            await operations_state.set_station_ready(user_data["station_id"], user_data["name"])
        elif station_message.readiness_state == "not_ready":
            await operations_state.set_station_not_ready(user_data["station_id"], user_data["name"])

        if station_message.message_type == MessageType.INCIDENT:
            await operations_state.activate_incident_mode()

        if station_message.operation_command in {"rz_stop", "rz_hold"}:
            await operations_state.activate_incident_mode()
            event_logger.log_event(
                "operation_action",
                {
                    "command": station_message.operation_command,
                    "actor": user_data["name"],
                    "role": user_data["role"],
                    "station_id": user_data["station_id"],
                },
            )

        resume_with_warnings, resume_missing_stations, should_continue = await _handle_resume_gate(
            websocket,
            station_message,
            user_data,
            message_data,
        )
        if should_continue:
            return

        if station_message.message_type == MessageType.HEARTBEAT:
            return

        event_logger.log_message(
            sender_pin=user_data["auth_id"],
            sender_name=user_data["name"],
            message_type=station_message.message_type.value,
            priority=station_message.priority.value,
            content=station_message.content,
            target_roles=station_message.target_roles,
        )

        broadcast_data = {
            "message_id": station_message.message_id,
            "timestamp": station_message.created_at.isoformat(),
            "sender": {
                "user_id": user_data["auth_id"],
                "name": user_data["name"],
                "role": user_data["role"],
                "station_id": user_data["station_id"],
                "phone": user_data.get("phone"),
            },
            "message_type": station_message.message_type.value,
            "priority": station_message.priority.value,
            "content": station_message.content,
            "created_at": station_message.created_at.isoformat(),
            "operation_command": station_message.operation_command,
            "readiness_state": station_message.readiness_state,
            "resume_with_warnings": resume_with_warnings,
            "missing_stations": resume_missing_stations,
        }
        broadcast_json = json.dumps(broadcast_data, ensure_ascii=False)

        exclude_pin = None if station_message.operation_command else user_data["auth_id"]

        if station_message.priority == MessagePriority.CRITICAL:
            await connection_manager.broadcast_critical(broadcast_json, exclude_pin=exclude_pin)
        elif station_message.target_roles:
            await connection_manager.broadcast_to_roles(
                broadcast_json,
                station_message.target_roles,
                exclude_pin=exclude_pin,
            )
        else:
            await connection_manager.broadcast_to_all(
                broadcast_json,
                exclude_pin=exclude_pin,
            )

    except json.JSONDecodeError:
        error_payload = {
            "type": "error",
            "message": "Invalid JSON format",
            "timestamp": datetime.utcnow().isoformat(),
        }
        await websocket.send_text(json.dumps(error_payload, ensure_ascii=False))
    except Exception as error:  # pragma: no cover - defensive fallback
        event_logger.log_error(
            "ws_message_error",
            str(error),
            {"auth_id": user_data["auth_id"][:10] + "..."},
        )
        error_payload = {
            "type": "error",
            "message": "Failed to process message",
            "timestamp": datetime.utcnow().isoformat(),
        }
        await websocket.send_text(json.dumps(error_payload, ensure_ascii=False))


@router.websocket("/ws/{auth_identifier}")
async def websocket_endpoint(websocket: WebSocket, auth_identifier: str) -> None:
    """WebSocket endpoint for real-time station communication.

    Args:
        websocket: WebSocket connection.
        auth_identifier: PIN code or session token.
    """
    user_data = await _resolve_user(auth_identifier)

    if not user_data:
        await websocket.close(code=1008, reason="Invalid authentication")
        event_logger.log_error(
            "ws_auth_failed",
            "Invalid auth identifier",
            {"auth_identifier": auth_identifier[:10] + "..."},
        )
        return

    await _register_user_connection(websocket, user_data)
    await _send_welcome_message(websocket, user_data)

    try:
        while True:
            data = await websocket.receive_text()
            await _process_message(websocket, user_data, data)
    except WebSocketDisconnect:
        connection_manager.disconnect(user_data["auth_id"])
        await vitality_monitor.mark_disconnected(user_data["auth_id"])
