# 🚀 RouterTools

> **AI-Powered OpenWrt Router Management & Recovery Toolkit**

A comprehensive toolkit that combines traditional router management with cutting-edge AI assistance, designed specifically for the **Netgear WNDR3700** router series running OpenWrt.

> ⚠️ **Important**: This toolkit has been developed and tested exclusively on the [Netgear WNDR3700](https://openwrt.org/toh/netgear/wndr3700) router. While some features may work on other OpenWrt devices, **use extreme caution** when using recovery tools on untested hardware.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![OpenWrt](https://img.shields.io/badge/OpenWrt-compatible-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Hardware](https://img.shields.io/badge/hardware-WNDR3700%20only-red.svg)

---

## ✨ Features

### 🤖 **AI-Powered Management**
- **Natural Language Interface**: Control your router using plain English commands
- **Intelligent Command Generation**: AI converts your requests into proper router commands
- **Interactive Terminal UI**: Beautiful split-screen interface with real-time logging

### 🔧 **Comprehensive Router Control**
- **SSH-Based Management**: Secure remote administration of OpenWrt routers
- **Package Management**: Install, update, and manage router packages
- **System Monitoring**: Real-time system information and status
- **USB Storage Setup**: Automated external storage configuration
- **VPN Configuration**: One-click NordVPN setup

### 🛠️ **Recovery Tools**
- **TFTP Firmware Recovery**: Recover bricked routers with automated TFTP transfer
- **Serial Console Access**: Hardware-level debugging via USB-to-UART bridge
- **Auto Network Detection**: Smart interface detection including USB adapters
- **Recovery Mode Guidance**: Step-by-step instructions for hardware recovery

---

## 🎯 Quick Start

### 1. **One-Command Setup**
```bash
git clone https://github.com/your-username/RouterTools.git
cd RouterTools
./scripts/setup_router_tools.sh
```

### 2. **Configure Environment**
```bash
# Required for AI features
export ANTHROPIC_API_KEY="your-claude-api-key"

# Optional router configuration
export ROUTER_PASS="your-router-password"
export ROUTER_HOST="192.168.1.1"  # if different
```

### 3. **Start Managing Your Router**
```bash
# Get system information
./router-cli info

# Use AI assistant
./router-cli ai --message "install htop and show me system resources"

# Launch fancy terminal UI
./router-ai
```

---

## 🎮 Usage Examples

### **Command Line Interface**

```bash
# 📊 System Information
./router-cli info

# 📦 Package Management
./router-cli packages update
./router-cli packages install htop nano
./router-cli packages list

# 💾 USB Storage Setup
./router-cli storage setup-usb

# 🔒 VPN Configuration
./router-cli vpn setup-nordvpn

# 🔧 Custom Commands
./router-cli exec 'uci show network'
```

### **AI Assistant**

```bash
# Interactive AI session
./router-cli ai

# Single AI command
./router-cli ai --message "check if my router needs any security updates"

# Complex operations
./router-cli ai --message "set up a guest network with bandwidth limits"
```

### **Terminal UI**

Launch the beautiful terminal interface:
```bash
./router-ai
```

**Features:**
- 💬 **Chat Tab**: Interactive AI conversation
- ⚡ **Commands Tab**: Real-time command execution
- 📝 **Auto-saving**: Chat history and command logs
- ⌨️ **Keyboard Shortcuts**: Efficient navigation

---

## 🆘 Recovery Tools & OpenWrt Installation

> ⚠️ **Critical Warning**: Recovery tools are designed specifically for **Netgear WNDR3700** hardware. Using these tools on other routers may cause permanent damage. Proceed only if you have the correct hardware!

> 🔌 **Hardware Required**: A [CP2102 USB-to-UART adapter](https://www.ebay.co.uk/itm/203604196200) is **essential** for firmware flashing and recovery operations. See the [WNDR3700 serial connection diagram](https://openwrt.org/_media/media/netgear/wndr3700/wndr3700_serial.jpg?w=400&tok=472e27) for proper wiring.

### **OpenWrt Firmware Recovery (TFTP)**
When your WNDR3700 router is bricked or needs OpenWrt installation:
```bash
sudo ./load-firmware
```

**What it does:**
- 🔍 Auto-detects network interfaces
- 🌐 Configures network for WNDR3700 recovery mode (192.168.1.1)
- 📡 Transfers OpenWrt firmware via TFTP (WNDR3700-specific timing)
- 🔄 Provides step-by-step WNDR3700 recovery guidance
- 💾 **Includes OpenWrt firmware** optimized for WNDR3700 hardware

**Prerequisites:**
- Ethernet connection to WNDR3700
- Router in recovery mode (power on while holding reset)
- OpenWrt-compatible firmware image (included in `firmware/` directory)

### **Serial Console Access & Firmware Flashing**
For hardware-level debugging and OpenWrt firmware flashing on WNDR3700:
```bash
sudo ./monitor-router
```

**Hardware Setup Required:**
- 🔌 **CP2102 USB-to-UART adapter** ([Example: CP2102 Module](https://www.ebay.co.uk/itm/203604196200))
- 📌 **Serial Header Connection**: Connect according to [WNDR3700 serial pinout diagram](https://openwrt.org/_media/media/netgear/wndr3700/wndr3700_serial.jpg?w=400&tok=472e27)
- 📡 **TX/RX**: Cross-connect (Router TX → Adapter RX, Router RX → Adapter TX)
- 🔧 **GND**: Ground connection
- ⚠️ **Do NOT connect VCC** - Router is self-powered, only connect RX, TX, and GND pins

**Features:**
- 🔍 Auto-detects CP2102 USB-to-UART devices
- 📺 Multiple terminal emulator support (picocom, screen, minicom)
- 🔧 WNDR3700-specific U-Boot command guidance for OpenWrt flashing
- 📋 Step-by-step OpenWrt firmware installation instructions

---

## 🏗️ Architecture

```
RouterTools/
├── 🐍 src/                     # Core Python modules
│   ├── router_manager.py       # SSH management layer
│   ├── router_cli.py          # Command-line interface
│   ├── router_ui.py           # Terminal UI (Textual)
│   └── anthropic_assistant.py # AI integration
├── 🔧 scripts/                # Recovery & setup tools
│   ├── load-firmware.sh       # TFTP recovery
│   ├── monitor-router.sh      # Serial monitoring
│   └── setup_router_tools.sh  # Installation script
├── 💾 firmware/               # OpenWrt firmware images for WNDR3700
├── 📦 bin/                    # Wrapper scripts
└── 📊 logs/                   # Application logs
```

### **Core Components**

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **RouterManager** | SSH operations | Secure router communication |
| **CLI Interface** | Command execution | Argparse-based commands |
| **Terminal UI** | Interactive interface | Textual framework, async |
| **AI Assistant** | Natural language | Claude API integration |

---

## 🔧 Installation Details

### **System Requirements**
- **OS**: Linux (Ubuntu/Debian recommended)
- **Python**: 3.8 or higher
- **Network**: Access to router (typically 192.168.1.1)
- **Router**: **Netgear WNDR3700 series only** (tested hardware)
- **Hardware for Serial Recovery**: [CP2102 USB-to-UART adapter](https://www.ebay.co.uk/itm/203604196200) **required** for firmware flashing and recovery operations

### **Dependencies**

**Python Packages:**
- `paramiko` - SSH client
- `requests` - HTTP client for AI API
- `rich` - Terminal formatting
- `textual` - Modern terminal UI
- `aiohttp` - Async HTTP support

**System Tools:**
- `atftp` - TFTP client for recovery
- `picocom/screen/minicom` - Serial communication
- `iputils-arping` - Network utilities

### **Manual Installation**
```bash
# Install system dependencies
sudo apt update
sudo apt install python3-venv python3-pip atftp picocom screen minicom

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x router-cli router-ai load-firmware monitor-router
```

---

## 🎨 AI Assistant Examples

The AI assistant can handle complex router management tasks using natural language:

### **Package Management**
```
You: "Install htop and check if there are any security updates"
AI: Executes: package install, security check, system status
```

### **Network Configuration**
```
You: "Set up a guest WiFi network with password 'GuestAccess123'"
AI: Configures: wireless interface, security settings, firewall rules
```

### **System Monitoring**
```
You: "Show me what's using the most CPU and memory"
AI: Installs monitoring tools, displays resource usage
```

### **Troubleshooting**
```
You: "My internet seems slow, can you diagnose the issue?"
AI: Runs network tests, checks connections, analyzes performance
```

---

## 🔒 Security & Best Practices

### **SSH Security**
- Uses paramiko with proper key management
- Supports password and key-based authentication
- Configurable timeouts and retry logic

### **API Security**
- Anthropic API key stored as environment variable
- No sensitive data logged or transmitted
- Local execution of all router commands

### **Recovery Safety**
- TFTP recovery includes validation steps for WNDR3700
- Serial monitoring is read-only by default
- Automated backups before major changes
- **Hardware verification**: Always confirm WNDR3700 model before recovery

---

## 🛠️ Troubleshooting

### **Common Issues**

| Problem | Solution |
|---------|----------|
| **Can't connect to router** | Check IP address, ensure SSH is enabled on OpenWrt |
| **AI commands fail** | Verify `ANTHROPIC_API_KEY` is set |
| **Permission denied** | Use `sudo` for recovery tools |
| **Serial device not found** | Check CP2102 USB-to-UART adapter connection to WNDR3700 serial headers |
| **Wrong router model** | ⚠️ **STOP** - Only use with WNDR3700 series! |

### **Debug Mode**
Enable verbose logging:
```bash
./router-cli --debug info
```

### **Network Issues**
Test connectivity:
```bash
ping 192.168.1.1
ssh root@192.168.1.1
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**: Follow existing code patterns
4. **Test thoroughly**: Verify with real router hardware
5. **Submit a pull request**: Describe your changes clearly

### **Development Setup**
```bash
git clone your-fork
cd RouterTools
./scripts/setup_router_tools.sh
source venv/bin/activate
```

---

## 📚 Advanced Usage

### **Custom Router Configuration**
```python
from src.router_manager import RouterConfig, OpenWrtManager

config = RouterConfig(
    host="192.168.1.1",
    username="root",
    password="your-password",
    port=22,
    timeout=30
)

manager = OpenWrtManager(config)
if manager.connect():
    result = manager.get_system_info()
    print(result)
```

### **Batch Operations**
```bash
# Multiple package installation
./router-cli ai --message "install htop, nano, wget, and curl"

# System optimization
./router-cli ai --message "optimize router performance and enable SQM"
```

### **OpenWrt Installation & Recovery**
```bash
# Automated OpenWrt firmware installation/recovery
sudo ./load-firmware --auto --firmware openwrt-wndr3700.bin

# Serial-assisted OpenWrt flashing (requires CP2102 adapter)
sudo ./monitor-router
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenWrt Project** - For the amazing router firmware
- **Anthropic** - For Claude AI API
- **Textual** - For the beautiful terminal UI framework

---

<div align="center">

**Made with ❤️ for the OpenWrt community**

[Report Bug](https://github.com/your-username/RouterTools/issues) • [Request Feature](https://github.com/your-username/RouterTools/issues) • [Documentation](https://github.com/your-username/RouterTools/wiki)

</div>