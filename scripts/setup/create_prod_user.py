#!/usr/bin/env python3
"""
Create production user script - direct MongoDB insertion
Usage: python create_prod_user.py <username> <email> <password>
"""

import asyncio
import sys
import os
from uuid import uuid4
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone

# Configure password hashing (same as app uses)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


async def create_user(username: str, email: str, password: str):
    """Create user directly in MongoDB"""

    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        print("❌ MONGODB_URL environment variable not set")
        return False

    print(f"🔍 Connecting to MongoDB...")

    try:
        client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")

        db = client.octavios
        users_collection = db.users

        # Check if user already exists
        existing = await users_collection.find_one({
            "$or": [{"username": username}, {"email": email}]
        })
        if existing:
            print(f"❌ User already exists: {existing.get('username')} / {existing.get('email')}")
            return False

        # Hash password
        hashed_password = pwd_context.hash(password)

        # Create user document
        user_doc = {
            "_id": str(uuid4()),
            "username": username,
            "email": email,
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

        result = await users_collection.insert_one(user_doc)
        print("✅ User created successfully!")
        print(f"   ID:       {result.inserted_id}")
        print(f"   Username: {username}")
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()


async def main():
    if len(sys.argv) != 4:
        print("Usage: python create_prod_user.py <username> <email> <password>")
        print("Example: python create_prod_user.py e_ipmoreno e_ipmoreno@bancoppel.com MyP@ssw0rd!")
        sys.exit(1)

    username, email, password = sys.argv[1], sys.argv[2], sys.argv[3]

    print(f"🚀 Creating user: {username} ({email})")
    print("=" * 50)

    success = await create_user(username, email, password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
