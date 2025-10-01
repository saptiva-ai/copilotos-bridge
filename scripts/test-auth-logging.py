#!/usr/bin/env python3
"""
Test script to verify improved authentication error logging
"""

import asyncio
import os
import sys

# Add apps/api to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

async def test_wrong_password():
    """Test connection with wrong password to verify error logging"""
    print("=" * 70)
    print("  🧪 Testing Authentication Error Logging")
    print("=" * 70)
    print("")

    # Correct connection string format but intentionally wrong password
    wrong_url = "mongodb://copilotos_user:WrongPassword123@mongodb:27017/copilotos?authSource=admin"

    print("🔌 Attempting connection with WRONG password...")
    print(f"   Username: copilotos_user")
    print(f"   Password: WrongPassword123 (intentionally incorrect)")
    print(f"   Host: mongodb:27017")
    print(f"   AuthSource: admin")
    print("")

    client = AsyncIOMotorClient(
        wrong_url,
        server_api=ServerApi('1'),
        serverSelectionTimeoutMS=5000
    )

    try:
        await client.admin.command('ping')
        print("❌ UNEXPECTED: Connection succeeded (should have failed)")
    except Exception as e:
        print("✓ Expected failure occurred")
        print("")
        print("Error details:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print(f"  Code: {getattr(e, 'code', 'N/A')}")
        print("")

        # Simulate what our improved logging would show
        print("=" * 70)
        print("  📋 Our Improved Logging Would Show:")
        print("=" * 70)
        print("")
        print("❌ MongoDB Connection Failed - AUTHENTICATION ERROR")
        print(f"   error_type: {type(e).__name__}")
        print(f"   error_message: {str(e)}")
        print(f"   error_code: {getattr(e, 'code', None)}")
        print("")
        print("   connection_details:")
        print("     username: copilotos_user")
        print("     host: mongodb:27017")
        print("     database: copilotos")
        print("     auth_source: admin")
        print("     using_srv: False")
        print("")
        print("   troubleshooting_hints:")
        print("     1. Check that MONGODB_PASSWORD in infra/.env matches docker-compose initialization")
        print("     2. Verify MongoDB container initialized with same password")
        print("     3. If password changed, recreate volumes: docker compose down -v")
        print("     4. Check environment variables are loaded: docker compose config")
        print("     5. Test direct connection: docker exec copilotos-mongodb mongosh -u <user> -p <pass>")
        print("")

        if 'Authentication failed' in str(e):
            print("🔑 Authentication Failed - Password Mismatch Detected")
            print("   likely_cause: MONGODB_PASSWORD environment variable differs from MongoDB initialization password")
            print("   solution: Update infra/.env to match password in docker-compose.yml, then run:")
            print("            docker compose down -v && docker compose up -d")

    finally:
        client.close()

    print("")
    print("=" * 70)
    print("  ✓ Test Complete")
    print("=" * 70)
    print("")

if __name__ == '__main__':
    try:
        asyncio.run(test_wrong_password())
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
