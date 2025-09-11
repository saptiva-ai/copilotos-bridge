// MongoDB initialization script
// This script runs when the container starts for the first time

// Switch to the application database
db = db.getSiblingDB('copilotos');

// Create application user with read/write permissions
db.createUser({
  user: 'copilotos_app',
  pwd: 'app_password_change_me',
  roles: [
    {
      role: 'readWrite',
      db: 'copilotos'
    }
  ]
});

// Create collections with validation schemas
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['username', 'email', 'password_hash'],
      properties: {
        username: {
          bsonType: 'string',
          description: 'Username must be a string and is required'
        },
        email: {
          bsonType: 'string',
          pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
          description: 'Email must be a valid email address and is required'
        },
        password_hash: {
          bsonType: 'string',
          description: 'Password hash must be a string and is required'
        },
        is_active: {
          bsonType: 'bool',
          description: 'Is active must be a boolean'
        },
        created_at: {
          bsonType: 'date',
          description: 'Created at must be a date'
        }
      }
    }
  }
});

// Create indexes for better performance
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "created_at": 1 });
db.users.createIndex({ "is_active": 1 });

// Chat sessions collection
db.createCollection('chat_sessions');
db.chat_sessions.createIndex({ "user_id": 1 });
db.chat_sessions.createIndex({ "created_at": 1 });
db.chat_sessions.createIndex({ "updated_at": -1 });
db.chat_sessions.createIndex({ "user_id": 1, "updated_at": -1 });

// Messages collection
db.createCollection('messages');
db.messages.createIndex({ "chat_id": 1 });
db.messages.createIndex({ "created_at": 1 });
db.messages.createIndex({ "role": 1 });
db.messages.createIndex({ "status": 1 });
db.messages.createIndex({ "chat_id": 1, "created_at": 1 });

// Tasks collection
db.createCollection('tasks');
db.tasks.createIndex({ "user_id": 1 });
db.tasks.createIndex({ "chat_id": 1 });
db.tasks.createIndex({ "status": 1 });
db.tasks.createIndex({ "type": 1 });
db.tasks.createIndex({ "created_at": 1 });
db.tasks.createIndex({ "user_id": 1, "created_at": -1 });

// Deep research tasks collection
db.createCollection('deep_research_tasks');
db.deep_research_tasks.createIndex({ "user_id": 1 });
db.deep_research_tasks.createIndex({ "query": "text" });
db.deep_research_tasks.createIndex({ "status": 1 });
db.deep_research_tasks.createIndex({ "created_at": 1 });

// Research sources collection
db.createCollection('research_sources');
db.research_sources.createIndex({ "task_id": 1 });
db.research_sources.createIndex({ "url": 1 });
db.research_sources.createIndex({ "domain": 1 });
db.research_sources.createIndex({ "source_type": 1 });
db.research_sources.createIndex({ "relevance_score": -1 });
db.research_sources.createIndex({ "credibility_score": -1 });

// Evidence collection
db.createCollection('evidence');
db.evidence.createIndex({ "task_id": 1 });
db.evidence.createIndex({ "support_level": 1 });
db.evidence.createIndex({ "confidence": -1 });
db.evidence.createIndex({ "claim": "text" });

print('MongoDB initialization completed successfully');
print('Database: copilotos');
print('Collections created with indexes');
print('Application user: copilotos_app (with readWrite permissions)');