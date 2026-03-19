#!/bin/bash
# Setup script for MCP Kanban Sync Server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Setting up MCP Kanban Sync Server..."

# Install dependencies
echo "Installing dependencies..."
cd "$SCRIPT_DIR"
npm install

# Build TypeScript
echo "Building TypeScript..."
npm run build

# Check for required env vars
if [ -z "$BACKEND_INTERNAL_KEY" ]; then
    echo ""
    echo "BACKEND_INTERNAL_KEY not set!"
    echo ""
    echo "To enable MongoDB sync, add to your shell config (~/.bashrc or ~/.zshrc):"
    echo ""
    echo "  export BACKEND_INTERNAL_KEY=\"YOUR_KEY_HERE\""
    echo ""
fi

# Check gh CLI auth
if ! gh auth status &>/dev/null; then
    echo ""
    echo "GitHub CLI not authenticated!"
    echo ""
    echo "Run: gh auth login"
    echo ""
fi

# Show .mcp.json config
echo ""
echo "Claude Code config (.mcp.json in project root):"
echo ""
cat << EOF
{
  "mcpServers": {
    "kanban-sync": {
      "type": "stdio",
      "command": "node",
      "args": ["$SCRIPT_DIR/dist/index.js"],
      "env": {
        "KANBAN_PATH": "./docs/kanban",
        "TRIAGE_PATH": "./docs/reports/feedback_triage",
        "BACKEND_URL": "http://localhost:18000",
        "BACKEND_INTERNAL_KEY": "\${BACKEND_INTERNAL_KEY}",
        "GITHUB_REPO": "saptiva-ai/octavios-chat-bajaware_invex"
      }
    }
  }
}
EOF
echo ""

echo "Setup complete!"
echo ""
echo "Usage:"
echo "  - Claude Code: MCP server auto-loads from .mcp.json"
echo ""
echo "Test locally:"
echo "  cd $SCRIPT_DIR && npm start"
