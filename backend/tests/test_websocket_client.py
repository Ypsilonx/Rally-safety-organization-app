"""WebSocket test client for Rally Safety App."""

import asyncio
import json
import sys
import websockets


async def test_websocket_connection(pin_code: str):
    """Test WebSocket connection and messaging.
    
    Args:
        pin_code: 4-digit PIN code for authentication
    """
    uri = f"ws://localhost:8000/ws/{pin_code}"
    
    print(f"📡 Připojuji se k {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Připojeno!")
            
            # Receive welcome message
            welcome = await websocket.recv()
            print(f"\n📨 Přijato: {welcome}")
            
            # Send test message
            test_message = {
                "message_type": "chat",
                "priority": "normal",
                "content": "Test zpráva z WebSocket klienta"
            }
            
            print(f"\n📤 Odesílám: {json.dumps(test_message, ensure_ascii=False)}")
            await websocket.send(json.dumps(test_message, ensure_ascii=False))
            
            # Wait for broadcast (optional - will timeout if no other clients)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"\n📨 Broadcast přijat: {response}")
            except asyncio.TimeoutError:
                print("\n⏱️ Žádný broadcast (jsem jediný klient)")
            
            print("\n✅ Test úspěšný!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Chyba připojení: {e}")
        print("   (Možná je PIN neplatný - zkontroluj server output)")
    except Exception as e:
        print(f"❌ Chyba: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Použití: python test_websocket_client.py <PIN>")
        print("   Příklad: python test_websocket_client.py 1234")
        sys.exit(1)
    
    pin = sys.argv[1]
    
    print("=" * 60)
    print("🧪 WebSocket Test Client")
    print("=" * 60)
    print(f"PIN: {pin}")
    print("=" * 60)
    asyncio.run(test_websocket_connection(pin))
