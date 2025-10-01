#!/bin/bash

# MCP Server runner for Claude Desktop
# NO output to stdout - only JSON-RPC allowed

cd "$(dirname "$0")" 2>/dev/null

# Clear environment
unset VIRTUAL_ENV 2>/dev/null

# Add UV to PATH
export PATH="$HOME/.local/bin:$PATH"

# Create venv if needed (silent)
[ ! -d ".venv" ] && uv venv >/dev/null 2>&1

# Install dependencies (silent)
uv pip install -r requirements.txt >/dev/null 2>&1

# Run server - only JSON-RPC goes to stdout
exec uv run --python .venv/bin/python python src/server.py 2>/dev/null