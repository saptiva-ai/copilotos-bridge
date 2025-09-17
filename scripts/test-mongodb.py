#!/usr/bin/env python3
"""
MongoDB connection test script
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError


async def test_mongodb_connection():
    """Test MongoDB connection"""
    # Default connection for local Docker setup
    mongodb_url = "mongodb://copilotos_user:secure_password_change_me@localhost:27017/copilotos"
    
    print("🔍 Testing MongoDB connection...")
    print(f"📍 URL: {mongodb_url.replace(':secure_password_change_me', ':secure_password_change_me')}")
    
    try:
        # Create client with short timeout for testing
        client = AsyncIOMotorClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        
        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        
        # Test database access
        db = client.copilotos
        
        # Test collection creation and basic operations
        test_collection = db.test_collection
        
        # Insert test document
        result = await test_collection.insert_one({"test": "data", "timestamp": "2024-01-01"})
        print(f"✅ Document inserted with ID: {result.inserted_id}")
        
        # Find test document
        doc = await test_collection.find_one({"_id": result.inserted_id})
        print(f"✅ Document retrieved: {doc}")
        
        # Delete test document
        await test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Test document cleaned up")
        
        # Test collection stats
        collections = await db.list_collection_names()
        print(f"📊 Available collections: {collections}")
        
        print("\n🎉 MongoDB test completed successfully!")
        return True
        
    except ServerSelectionTimeoutError:
        print("❌ MongoDB connection timeout")
        print("   Make sure MongoDB is running on localhost:27017")
        print("   Run: docker compose -f infra/docker/docker-compose.yml up -d mongodb")
        return False
        
    except Exception as e:
        print(f"❌ MongoDB connection error: {str(e)}")
        return False
        
    finally:
        if 'client' in locals():
            client.close()


def print_connection_help():
    """Print connection help"""
    print("\n📖 MongoDB Setup Help:")
    print("   1. Start MongoDB with Docker:")
    print("      docker compose -f infra/docker/docker-compose.yml up -d mongodb")
    print("\n   2. Check if MongoDB is running:")
    print("      docker ps | grep mongodb")
    print("\n   3. View MongoDB logs:")
    print("      docker logs copilotos-mongodb")
    print("\n   4. Connect with MongoDB shell:")
    print("      docker exec -it copilotos-mongodb mongosh -u copilotos_user -p secure_password_change_me")


async def main():
    """Main function"""
    success = await test_mongodb_connection()
    
    if not success:
        print_connection_help()
        sys.exit(1)
    
    print("\n✅ All MongoDB tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
