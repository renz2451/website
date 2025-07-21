#!/data/data/com.termux/files/usr/bin/bash

echo "📡 Starting RENZ Dumper Server..."

# 1. Start Flask in background
nohup python app.py > /dev/null 2>&1 &
sleep 3

# 2. Start LocalTunnel
echo "🌍 Opening public tunnel..."
lt --port 5051 --open false
