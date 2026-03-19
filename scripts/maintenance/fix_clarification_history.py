
import asyncio
import os
import motor.motor_asyncio
from pymongo import UpdateOne

# Default credentials matching docker-compose.yml
MONGO_URI = os.getenv("MONGO_URI", "mongodb://octavios_user:secure_password_change_me@localhost:27018")
DB_NAME = os.getenv("MONGO_DB", "octavios")

async def fix_history():
    print(f"🔌 Connecting to MongoDB at {MONGO_URI.split('@')[-1]}...")
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db.history_events
    
    # 1. Find all history events that are clarifications but missing "clarifications" key
    # Only check assistant messages or specific clarification types
    # Based on streaming_handler, the metadata is saved in "bank_clarification_data" inside the payload usually?
    # Wait, history events have a specific structure.
    # In streaming_handler.py:
    # assistant_metadata["bank_clarification_data"] = ...
    # assistant_message = await chat_service.add_assistant_message(..., metadata=assistant_metadata)
    
    # ChatService records this to history via HistoryService.record_chat_message
    # The ChatEventData is stored in 'chat_data' field, and it has 'metadata'
    
    print("🔍 Scanning for broken clarification events (in chat_data.metadata)...")
    
    # Path: chat_data.metadata.bank_clarification_data
    
    query = {
        "chat_data.metadata.bank_clarification_data": {"$exists": True},
        "chat_data.metadata.bank_clarification_data.options": {"$exists": True},
        "chat_data.metadata.bank_clarification_data.clarifications": {"$exists": False}
    }
    
    cursor = collection.find(query)
    bulk_ops = []
    count = 0
    
    async for doc in cursor:
        # Access nested path safely
        try:
            clar_data = doc["chat_data"]["metadata"]["bank_clarification_data"]
        except KeyError:
            continue
            
        options = clar_data.get("options", [])
        
        # Construct legacy clarifications
        frontend_options = []
        for opt in options:
            frontend_options.append({
                "value": opt.get("id"),
                "label": opt.get("label") or opt.get("id")
            })
            
        legacy_clarifications = [{
            "field": "selected_option",
            "question": clar_data.get("message", "Please select an option"),
            "options": frontend_options
        }]
        
        # Prepare update
        # Path: chat_data.metadata.bank_clarification_data.clarifications
        update_path = "chat_data.metadata.bank_clarification_data.clarifications"
        
        op = UpdateOne(
            {"_id": doc["_id"]},
            {"$set": {update_path: legacy_clarifications}}
        )
        bulk_ops.append(op)
        count += 1
        
        if len(bulk_ops) >= 100:
            await collection.bulk_write(bulk_ops)
            bulk_ops = []
            print(f"   Processed {count} documents...")

    if bulk_ops:
        await collection.bulk_write(bulk_ops)
        
    print(f"✅ Finished! Fixed {count} documents.")

if __name__ == "__main__":
    try:
        asyncio.run(fix_history())
    except Exception as e:
        print(f"❌ Error: {e}")
