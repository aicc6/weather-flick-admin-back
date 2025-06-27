import uvicorn
import os
import sys

if __name__ == "__main__":
    try:
        print("🚀 Starting Weather Flick Admin Backend Server...")
        print("📍 Server will be available at: http://localhost:8000")
        print("📊 Admin API Documentation: http://localhost:8000/docs")
        print("🔄 Auto-reload enabled for development")
        print("-" * 50)

        uvicorn.run(
            "app.main:app",  # import string instead of app object
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
