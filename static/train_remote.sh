#!/bin/bash
clear
echo "=========================================="
echo "          ARCS Remote Worker"
echo "=========================================="
echo ""

LAST_URL_FILE=".last_robot_url"
DEFAULT_URL="http://192.168.1.50:5000"

if [ -f "$LAST_URL_FILE" ]; then
    SAVED_URL=$(cat "$LAST_URL_FILE")
fi

if [ -z "$SAVED_URL" ]; then
    read -p "Robot URL (e.g. $DEFAULT_URL): " ROBOT_URL
else
    read -p "Robot URL [Enter for $SAVED_URL]: " ROBOT_URL
fi

if [ -z "$ROBOT_URL" ]; then
    if [ -n "$SAVED_URL" ]; then
        ROBOT_URL="$SAVED_URL"
    else
        ROBOT_URL="$DEFAULT_URL"
    fi
fi

echo "$ROBOT_URL" > "$LAST_URL_FILE"
echo ""

echo "[1/3] Installing/Updating dependencies..."
pip3 install --upgrade lerobot requests huggingface_hub -q

echo ""
echo "[2/3] Checking HuggingFace Login..."
if ! python3 -m huggingface_hub.commands.huggingface_cli whoami > /dev/null 2>&1; then
    echo ""
    echo "Login required. Please paste your token below:"
    python3 -m huggingface_hub.commands.huggingface_cli login
else
    echo "Already logged in."
fi
echo ""

echo "[3/3] Starting worker..."
echo ""

while true; do
    python3 -c "import requests; exec(requests.get('${ROBOT_URL}/static/worker.py').text)" "$ROBOT_URL"
    sleep 5
done
