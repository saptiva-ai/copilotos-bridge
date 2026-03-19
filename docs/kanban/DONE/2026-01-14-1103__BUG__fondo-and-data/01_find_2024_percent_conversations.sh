#!/bin/bash
# Script to find conversations with "2024%" bug
# Credentials referenced from envs/.env

set -e

echo "===== Finding messages with '2024%' bug ====="

ssh -o StrictHostKeyChecking=no ${PROD_SERVER_USER}@${PROD_SERVER_IP} 'docker exec octavios-chat-bajaware_invex-mongodb mongosh "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" --quiet --eval "
db.messages.find(
  { content: /2024%/ },
  { _id: 1, chat_id: 1, role: 1, content: 1, created_at: 1 }
).sort({ created_at: -1 }).limit(10).toArray()
"'

echo ""
echo "===== Extracting specific conversation with IMOR/ICAP bug ====="

ssh -o StrictHostKeyChecking=no ${PROD_SERVER_USER}@${PROD_SERVER_IP} 'docker exec octavios-chat-bajaware_invex-mongodb mongosh "mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin" --quiet --eval "
// Get the conversation ID from one of the messages with 2024%
var bugMessage = db.messages.findOne({ content: /IMOR del.*2024%/ });
var chatId = bugMessage ? bugMessage.chat_id : \"ef29d621-6de0-426f-af63-aab70a1b999a\";

print(\"\\n===== Chat ID: \" + chatId + \" =====\");

// Get all messages in this conversation
db.messages.find(
  { chat_id: chatId },
  { _id: 1, role: 1, content: 1, created_at: 1, metadata: 1 }
).sort({ created_at: 1 }).limit(20).toArray()
"'
