#!/bin/bash
# Script to find artifacts for the conversation with IMOR/ICAP bug
# Credentials referenced from envs/.env

set -e

CHAT_ID="${1:-ef29d621-6de0-426f-af63-aab70a1b999a}"

echo "===== Finding artifacts for chat_id: $CHAT_ID ====="

ssh -o StrictHostKeyChecking=no ${PROD_SERVER_USER}@${PROD_SERVER_IP} "docker exec octavios-chat-bajaware_invex-mongodb mongosh \"mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin\" --quiet --eval \"
db.artifacts.find(
  { chat_session_id: '$CHAT_ID' },
  {
    _id: 1,
    title: 1,
    type: 1,
    'content.metric_name': 1,
    'content.bank_names': 1,
    'content.response_text': 1,
    'content.data_as_of': 1,
    'content.metadata': 1,
    'content.chart_status': 1,
    created_at: 1
  }
).sort({ created_at: -1 }).toArray()
\""

echo ""
echo "===== Getting full artifact detail for IMOR chart ====="

ssh -o StrictHostKeyChecking=no ${PROD_SERVER_USER}@${PROD_SERVER_IP} "docker exec octavios-chat-bajaware_invex-mongodb mongosh \"mongodb://${MONGODB_USER}:${MONGODB_PASSWORD}@localhost:27017/${MONGODB_DATABASE}?authSource=admin\" --quiet --eval \"
db.artifacts.findOne(
  {
    chat_session_id: '$CHAT_ID',
    'content.metric_name': 'IMOR'
  }
)
\""
