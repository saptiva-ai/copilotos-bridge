#!/bin/bash
# Script to find clarification messages (button vs input form issue)
# Credentials referenced from envs/.env

set -e

echo "===== Finding clarification messages ====="

ssh -o StrictHostKeyChecking=no ${PROD_SERVER_USER}@${PROD_SERVER_IP} 'docker exec octavios-chat-bajaware_invex-mongodb mongosh "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" --quiet --eval "
db.messages.find(
  {
    \$or: [
      { content: /Necesito un poco más de información/i },
      { content: /¿De qué banco o institución financiera/i },
      { content: /¿Para qué periodo de tiempo necesitas/i },
      { content: /Por favor.*especifica/i }
    ]
  },
  { _id: 1, chat_id: 1, content: 1, metadata: 1, created_at: 1 }
).sort({ created_at: -1 }).limit(10).toArray()
"'

echo ""
echo "===== Looking for artifacts with clarification type ====="

ssh -o StrictHostKeyChecking=no ${PROD_SERVER_USER}@${PROD_SERVER_IP} 'docker exec octavios-chat-bajaware_invex-mongodb mongosh "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" --quiet --eval "
db.artifacts.find(
  { type: \"clarification\" },
  { _id: 1, chat_session_id: 1, title: 1, content: 1, created_at: 1 }
).sort({ created_at: -1 }).limit(5).toArray()
"'
