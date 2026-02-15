"""Rally Safety App - FastAPI Backend."""

import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.api.auth import router as auth_router
from backend.core.auth import auth_manager
from backend.core.config import get_settings
from backend.core.connection_manager import connection_manager
from backend.core.event_logger import event_logger
from backend.models.message import StationMessage, MessagePriority
from backend.models.user import UserRole

# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS middleware - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)


@app.on_event("startup")
async def startup_event():
    """Generate test PINs on server startup for MVP testing."""
    # Generate test komisař PINs
    komisar1 = auth_manager.generate_pin(
        name="Jan Testovací",
        role=UserRole.KOMISAR_TRAT,
        phone="+420123456789",
        station_id="TK-01"
    )
    
    komisar2 = auth_manager.generate_pin(
        name="Eva Zkušební",
        role=UserRole.KOMISAR_ZATACKA,
        phone="+420987654321",
        station_id="ZT-05"
    )
    
    print("=" * 60)
    print("🔐 TESTOVACÍ PŘIHLAŠOVACÍ ÚDAJE")
    print("=" * 60)
    print("\n📋 VEDENÍ RZ (Username + Password):")
    print("   Username: admin")
    print("   Password: demo123")
    print("\n📋 KOMISAŘI (PIN kód):")
    print(f"   Komisař 1: {komisar1.name}")
    print(f"   PIN: {komisar1.pin_code}")
    print(f"   Role: {komisar1.role.value}")
    print(f"   Stanice: {komisar1.station_id}")
    print()
    print(f"   Komisař 2: {komisar2.name}")
    print(f"   PIN: {komisar2.pin_code}")
    print(f"   Role: {komisar2.role.value}")
    print(f"   Stanice: {komisar2.station_id}")
    print("\n" + "=" * 60)
    print(f"✅ Server běží na http://{settings.HOST}:{settings.PORT}")
    print("=" * 60)


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "active_connections": connection_manager.get_active_count()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": connection_manager.get_active_count(),
        "max_connections": settings.WS_MAX_CONNECTIONS
    }


@app.websocket("/ws/{pin_code}")
async def websocket_endpoint(websocket: WebSocket, pin_code: str):
    """WebSocket endpoint for real-time communication.
    
    Args:
        websocket: WebSocket connection
        pin_code: 4-digit PIN code for authentication
    """
    # Verify PIN before accepting connection
    komisar = auth_manager.verify_pin(pin_code)
    
    if not komisar:
        await websocket.close(code=1008, reason="Invalid PIN code")
        event_logger.log_error(
            "ws_auth_failed",
            "Invalid PIN attempt",
            {"pin_code": pin_code}
        )
        return
    
    # Accept connection and register
    await connection_manager.connect(
        websocket=websocket,
        pin_code=pin_code,
        name=komisar.name,
        role=komisar.role.value,
        station_id=komisar.station_id
    )
    
    # Send welcome message
    welcome_msg = {
        "type": "system",
        "message": f"Vítejte, {komisar.name}! Připojeno.",
        "timestamp": datetime.utcnow().isoformat(),
        "active_users": connection_manager.get_active_count()
    }
    await websocket.send_text(json.dumps(welcome_msg, ensure_ascii=False))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                
                # Create StationMessage
                station_message = StationMessage(
                    message_id=f"msg_{datetime.utcnow().timestamp()}",
                    sender_pin=pin_code,
                    sender_name=komisar.name,
                    message_type=message_data.get("message_type", "chat"),
                    priority=message_data.get("priority", "normal"),
                    content=message_data.get("content", ""),
                    target_roles=message_data.get("target_roles")
                )
                
                # Log the message
                event_logger.log_message(
                    sender_pin=pin_code,
                    sender_name=komisar.name,
                    message_type=station_message.message_type.value,
                    priority=station_message.priority.value,
                    content=station_message.content,
                    target_roles=station_message.target_roles
                )
                
                # Prepare message for broadcast
                broadcast_data = {
                    "message_id": station_message.message_id,
                    "timestamp": station_message.created_at.isoformat(),
                    "sender_pin": station_message.sender_pin,
                    "sender_name": station_message.sender_name,
                    "message_type": station_message.message_type.value,
                    "priority": station_message.priority.value,
                    "content": station_message.content
                }
                broadcast_json = json.dumps(broadcast_data, ensure_ascii=False)
                
                # Selective broadcast based on target_roles and priority
                if station_message.priority == MessagePriority.CRITICAL:
                    # Critical messages go to everyone
                    await connection_manager.broadcast_critical(broadcast_json)
                
                elif station_message.target_roles:
                    # Send to specific roles only
                    await connection_manager.broadcast_to_roles(
                        broadcast_json,
                        station_message.target_roles,
                        exclude_pin=pin_code
                    )
                
                else:
                    # Normal broadcast to all
                    await connection_manager.broadcast_to_all(
                        broadcast_json,
                        exclude_pin=pin_code
                    )
            
            except json.JSONDecodeError:
                error_msg = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_msg, ensure_ascii=False))
            
            except Exception as e:
                event_logger.log_error(
                    "ws_message_error",
                    str(e),
                    {"pin_code": pin_code}
                )
                error_msg = {
                    "type": "error",
                    "message": "Failed to process message",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_msg, ensure_ascii=False))
    
    except WebSocketDisconnect:
        connection_manager.disconnect(pin_code)


@app.get("/api/stats")
async def get_stats():
    """Get current system statistics.
    
    Returns:
        Statistics about active connections, roles, etc.
    """
    return {
        "active_connections": connection_manager.get_active_count(),
        "max_connections": settings.WS_MAX_CONNECTIONS,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/debug/pins")
async def debug_list_pins():
    """Debug endpoint - list all generated PINs (DEVELOPMENT ONLY).
    
    Returns:
        List of all generated komisař PINs
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")
    
    pins = auth_manager.list_all_pins()
    return {
        "total": len(pins),
        "pins": [
            {
                "pin_code": p.pin_code,
                "name": p.name,
                "role": p.role.value,
                "station_id": p.station_id,
                "phone": p.phone
            }
            for p in pins
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
