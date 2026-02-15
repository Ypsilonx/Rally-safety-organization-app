"""Helper script to display PINs from running server.

NOTE: This script fetches PINs from the server via API.
It does NOT generate new PINs (that would create separate instance).
"""

import httpx
import sys


def get_server_pins(base_url: str = "http://localhost:8000"):
    """Get PINs from running server via debug API.
    
    Args:
        base_url: Server base URL
        
    Returns:
        List of PIN data or None if server not running
    """
    try:
        response = httpx.get(f"{base_url}/api/debug/pins", timeout=5)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        print("❌ Server neběží! Spusť nejdřív server:")
        print("   uvicorn backend.main:app --reload")
        return None
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return None


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("=" * 60)
    print("🔐 PŘIHLAŠOVACÍ ÚDAJE ZE SERVERU")
    print("=" * 60)
    
    data = get_server_pins(base_url)
    
    if data:
        print("\n📋 VEDENÍ RZ (Username + Password):")
        print("   Username: admin")
        print("   Password: demo123")
        print("\n📋 KOMISAŘI (PIN kód):")
        
        for pin_data in data["pins"]:
            print(f"\n   {pin_data['name']}")
            print(f"   PIN: {pin_data['pin_code']}")
            print(f"   Role: {pin_data['role']}")
            print(f"   Stanice: {pin_data['station_id']}")
        
        print("\n" + "=" * 60)
        print(f"📊 Celkem PINů: {data['total']}")
        print("=" * 60)
