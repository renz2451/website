#!/data/data/com.termux/files/usr/bin/bash

echo "🛑 Stopping Flask and LocalTunnel..."

# Kill Flask server
pkill -f "python /storage/emulated/0/Download/renz_web_dumper_final/app.py"

# Kill LocalTunnel
pkill -f "lt --port"
echo "✅ All stopped."
