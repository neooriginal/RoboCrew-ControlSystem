#!/bin/bash
#
# ARCS One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/neooriginal/ARCS/main/install.sh | bash
#

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "    _    ____   ____ ____  "
echo "   / \  |  _ \ / ___/ ___| "
echo "  / _ \ | |_) | |   \___ \ "
echo " / ___ \|  _ <| |___ ___) |"
echo "/_/   \_\_| \_\\____|____/ "
echo -e "${NC}"
echo -e "${GREEN}Autonomous Robot Control System - Installer${NC}"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    echo "Please install Python 3.10+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"

# Check for git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: Git is required but not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git detected"

# Install directory
INSTALL_DIR="${HOME}/ARCS"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Warning: $INSTALL_DIR already exists.${NC}"
    read -p "Overwrite? (y/N): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    rm -rf "$INSTALL_DIR"
fi

echo ""
echo -e "${CYAN}[1/4]${NC} Cloning ARCS repository..."
git clone --depth 1 https://github.com/neooriginal/ARCS.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo -e "${CYAN}[2/4]${NC} Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo -e "${CYAN}[3/54]${NC} Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo -e "${CYAN}[4/4]${NC} Setting up environment..."
cp .env.example .env

# Prompt for API key (Moved to Settings UI)
echo ""
echo -e "${YELLOW}Note: Configure your OpenAI API Key in the Web UI Settings after installation.${NC}"

# Install system dependencies (Linux only)
if command -v apt-get &> /dev/null; then
    echo ""
    echo -e "${YELLOW}Install audio dependencies (mpg123)? Requires sudo. (y/N):${NC}"
    read -p "" INSTALL_AUDIO
    if [[ "$INSTALL_AUDIO" =~ ^[Yy]$ ]]; then
        sudo apt-get install -y mpg123
    fi
fi

# Systemd Service Installation (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v systemctl &> /dev/null; then
    echo ""
    echo -e "${YELLOW}Install as a systemd service (auto-start)? Requires sudo. (y/N):${NC}"
    read -p "" INSTALL_SERVICE
    if [[ "$INSTALL_SERVICE" =~ ^[Yy]$ ]]; then
        SERVICE_FILE="/etc/systemd/system/arcs.service"
        USER_NAME=$(whoami)
        
        echo -e "${CYAN}Creating service file at $SERVICE_FILE...${NC}"

        # Write service file with sudo
        sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=ARCS - Autonomous Robot Control System
After=network.target sound.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

        echo -e "${CYAN}Enabling and starting service...${NC}"
        sudo systemctl daemon-reload
        sudo systemctl enable arcs.service
        sudo systemctl start arcs.service
        
        echo -e "${GREEN}✓ Service installed and started!${NC}"
        echo "Check status with: sudo systemctl status arcs.service"
        echo "View logs with: sudo journalctl -u arcs -f"
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Installation Complete! 🎉            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Directory: ${CYAN}$INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. cd $INSTALL_DIR"
echo "  2. source venv/bin/activate"
echo "  3. python main.py"
echo ""
echo -e "Open ${CYAN}http://localhost:5000/settings${NC} to configure hardware."
echo ""
