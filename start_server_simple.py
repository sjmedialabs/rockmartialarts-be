#!/usr/bin/env python3
"""
Simple server starter
"""
import uvicorn
from server import app

if __name__ == "__main__":
    print("🚀 Starting Marshalats Backend Server...")
    print("📍 Server will be available at: https://rockmartialartsacademy.com")
    print("📖 API Documentation: https://rockmartialartsacademy.com/docs")
    print("=" * 50)
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8003,
            log_level="info",
            access_log=True,
            reload=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
