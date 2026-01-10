#!/bin/bash
# Enable a private HTTPS tunnel for your tailnet only
echo "Configuring private Tailscale Serve..."

# 1. This maps Ollama (11434) to a standard HTTPS port (443) 
# only accessible to YOUR devices.
tailscale serve --bg 11434

echo "------------------------------------------------"
echo "Tunnel is active! Use this URL in Cline/Laptop:"
tailscale status --json | jq -r '.Self.DNSName' | sed 's/\.$//' | xargs -I {} echo "https://{}"
echo "------------------------------------------------"