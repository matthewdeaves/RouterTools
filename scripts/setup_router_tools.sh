#!/bin/bash

echo "🚀 Setting up Router Management Tools with all dependencies..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# Function to check if running as root
check_sudo() {
    if [ "$EUID" -eq 0 ]; then
        echo "❌ Please don't run this script as root. It will ask for sudo when needed."
        exit 1
    fi
}

# Function to install system dependencies
install_system_deps() {
    echo "📦 Installing system dependencies..."
    echo "This script requires root privileges to:"
    echo "- Install system packages: python3-venv, python3-full, atftp, iputils-arping, iproute2, picocom"
    echo "- Install serial communication tools: screen, minicom"
    echo ""
    echo "Please enter your sudo password when prompted:"
    
    sudo apt-get update -qq
    sudo apt-get install -y \
        python3-venv \
        python3-full \
        python3-pip \
        atftp \
        iputils-arping \
        iproute2 \
        picocom \
        screen \
        minicom
        
    echo "✅ System dependencies installed successfully!"
}

# Check sudo access and install system dependencies
check_sudo
install_system_deps

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment and install dependencies
echo "Installing Python dependencies in virtual environment..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Make scripts executable
chmod +x anthropic_assistant.py
chmod +x router_manager.py

# Create wrapper scripts that automatically use the virtual environment
echo "Creating wrapper scripts..."

# Create router-ai wrapper  
cat > router-ai << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
exec python "$SCRIPT_DIR/src/router_ui.py" "$@"
EOF
chmod +x router-ai

# Create symlink for global access (optional)
if [ "$1" = "--install-global" ]; then
    sudo ln -sf "$SCRIPT_DIR/router-ai" /usr/local/bin/router-ai
    echo "Installed router-ai globally"
fi

echo "🎉 Setup complete!"
echo ""
echo "📋 Everything installed:"
echo "  ✅ Python virtual environment with all dependencies"
echo "  ✅ Router recovery tools (atftp, picocom, etc.)"
echo "  ✅ Network utilities (arping, ip commands)"
echo "  ✅ Serial communication tools (screen, minicom)"
echo ""
echo "🚀 Usage examples:"
echo "  # 🎨 AI ASSISTANT with split-screen UI!"
echo "  export ANTHROPIC_API_KEY='your-api-key'"
echo "  export ROUTER_PASS='your-password'"
echo "  ./router-ai"
echo ""
echo "  # Use natural language for all router operations:"
echo "  - 'Get router system info'"
echo "  - 'Update packages'"
echo "  - 'Install htop package'"
echo "  - 'Setup USB storage'"
echo "  - 'Setup NordVPN'"
echo "  - 'Show network configuration'"
echo ""
echo "🔧 Recovery tools:"
echo "  # TFTP recovery (requires root)"
echo "  sudo ./load-firmware"
echo ""
echo "  # Serial monitoring"
echo "  sudo ./monitor-router"
echo ""
echo "💡 Note: All commands automatically use the virtual environment."
echo "    No need to manually activate it!"