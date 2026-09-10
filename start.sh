#!/bin/bash

cd /workspaces/PrivateAIRoom

# Stop duplicate bot processes
pkill -9 -f "python bot.py" 2>/dev/null || true

# Make recovery storage valid
if [ ! -s conversation_recovery.json ]; then
    printf '{}\n' > conversation_recovery.json
fi

# Start bot
nohup python bot.py > bot.log 2>&1 &

echo "PRIVATE AI ROOM STARTED"
echo "PID: $!"
