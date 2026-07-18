"""Rally Safety App - FastAPI backend application setup."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.api.auth import router as auth_router
from backend.api.admin import router as admin_router
from backend.api.audit import router as audit_router
from backend.api.status import router as status_router
from backend.api.websocket import router as websocket_router
from backend.core.auth import auth_manager
from backend.core.config import get_settings
from backend.core.connection_manager import connection_manager
from backend.services.vitality import vitality_monitor

async def _startup() -> None:
    """Load existing PINs and start background services."""
    await vitality_monitor.start()

    # Load existing PINs from data/pins.json (persistent storage)
    all_pins = auth_manager.list_all_pins()

    print("=" * 60)
    print("🔐 PŘIHLAŠOVACÍ ÚDAJE")
    print("=" * 60)
    print("\n📋 VEDENÍ RZ (Username + Password):")
    print("   VRZ   / demo123")
    print("   ZVRZ  / demo123")
    print("   VBRZ  / demo123")
    print("   ZVBRZ / demo123")
    print("   admin / demo123 (technický fallback)")

    if all_pins:
        print("\n📋 KOMISAŘI (PIN kód):")
        for komisar in all_pins:
            print(f"\n   {komisar.name}")
            print(f"   PIN: {komisar.pin_code}")
            print(f"   Role: {komisar.role.value}")
            print(f"   Stanice: {komisar.station_id or 'Nepřiřazena'}")
    else:
        print("\n⚠️  ŽÁDNÉ KOMISAŘ PINy - použij Admin Panel pro generování")

    print("\n" + "=" * 60)
    print(f"✅ Server běží na http://{settings.HOST}:{settings.PORT}")
    print(f"📊 Načteno PINů: {len(all_pins)}")
    print("=" * 60)


async def _shutdown() -> None:
    """Gracefully stop background services."""
    await vitality_monitor.stop()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage FastAPI startup/shutdown lifecycle."""
    await _startup()
    try:
        yield
    finally:
        await _shutdown()


# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
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
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(status_router)
app.include_router(websocket_router)


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
