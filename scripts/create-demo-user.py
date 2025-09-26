#!/usr/bin/env python3
"""
Create demo user script - works with Docker setup
"""

import asyncio
import sys
import os
from uuid import uuid4
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone

# Configure password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Demo user credentials
DEMO_USER = {
    "username": "demo_admin",
    "email": "demo@saptiva.ai",
    "password": "ChangeMe123!",
}

async def create_demo_user():
    """Create demo user directly in MongoDB"""

    # MongoDB connection from environment or default
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos")

    print("🔍 Connecting to MongoDB...")
    print(f"📍 URL: {mongodb_url.split('@')[0]}@[hidden]/{mongodb_url.split('/')[-1]}")

    try:
        # Create client
        client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)

        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")

        # Get database
        db = client.copilotos
        users_collection = db.users

        # Check if user already exists
        existing_user = await users_collection.find_one({"username": DEMO_USER["username"]})
        if existing_user:
            print("ℹ️  Demo user already exists. Skipping creation.")
            print(f"   Username: {DEMO_USER['username']}")
            print(f"   Email:    {DEMO_USER['email']}")
            return True

        # Hash password
        hashed_password = pwd_context.hash(DEMO_USER["password"])

        # Create user document
        user_doc = {
            "_id": str(uuid4()),
            "username": DEMO_USER["username"],
            "email": DEMO_USER["email"],
            "password_hash": hashed_password,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "preferences": {
                "theme": "dark",
                "language": "es",
                "default_model": "SAPTIVA_CORTEX",
                "chat_settings": {}
            }
        }

        # Insert user
        result = await users_collection.insert_one(user_doc)
        print("✅ Demo user created successfully!")
        print(f"   ID:       {result.inserted_id}")
        print(f"   Username: {DEMO_USER['username']}")
        print(f"   Email:    {DEMO_USER['email']}")
        print(f"   Password: {DEMO_USER['password']}")
        print("\n🎉 You can now login with these credentials!")

        return True

    except Exception as e:
        print(f"❌ Error creating demo user: {e}")
        return False

    finally:
        if 'client' in locals():
            client.close()

async def main():
    """Main function"""
    print("🚀 Creating demo user for Copilotos Bridge...")
    print("=" * 50)

    success = await create_demo_user()

    if not success:
        print("\n📖 Troubleshooting:")
        print("   1. Make sure MongoDB is running:")
        print("      make dev")
        print("   2. Check container status:")
        print("      docker ps | grep mongodb")
        sys.exit(1)

    print("\n✅ Demo user setup completed!")

if __name__ == "__main__":
    asyncio.run(main())
