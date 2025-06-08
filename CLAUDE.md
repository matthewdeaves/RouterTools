# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RouterTools is a comprehensive toolkit for managing OpenWrt routers (specifically WNDR3700 series) that combines traditional SSH-based router management with AI-powered assistance using Anthropic's Claude API.

## Architecture

### Core Components
- **`src/router_manager.py`**: Core SSH management layer with `OpenWrtManager` class for router operations
- **`src/router_ui.py`**: Advanced Textual-based terminal UI with tabbed interface and real-time logging
- **`src/anthropic_assistant.py`**: AI integration layer that converts natural language to router commands

### Recovery Tools
- **`scripts/load-firmware.sh`**: TFTP-based firmware recovery with auto network detection
- **`scripts/monitor-router.sh`**: Serial console monitoring via CP2102 USB-to-UART bridge
- **`scripts/setup_router_tools.sh`**: Complete installation and dependency setup

## Common Development Commands

### Setup and Installation
```bash
# Initial setup (installs system deps and creates venv)
./scripts/setup_router_tools.sh

# Install globally (optional)
./scripts/setup_router_tools.sh --install-global
```

### Running the Applications
```bash
# AI-powered terminal UI (requires ROUTER_PASS env var)
export ANTHROPIC_API_KEY='your-api-key'
export ROUTER_PASS='your-password'
./router-ai

# Recovery tools (require root)
sudo ./load-firmware
sudo ./monitor-router
```

### Testing and Validation
No formal test suite exists. Manual testing involves:
- SSH connectivity to OpenWrt router at 192.168.1.1
- AI command parsing and execution validation
- Recovery tool functionality with bricked router

## Environment Variables

### Required for AI Features
- `ANTHROPIC_API_KEY`: Required for AI assistant functionality

### Optional Configuration
- `ROUTER_HOST`: Router IP (default: 192.168.1.1)
- `ROUTER_USER`: SSH username (default: root)
- `ROUTER_PASS`: SSH password
- `ROUTER_PORT`: SSH port (default: 22)

## Dependencies

### Python Dependencies (requirements.txt)
- `paramiko>=2.7.0`: SSH client
- `requests>=2.25.0`: HTTP client for Anthropic API
- `rich>=13.0.0`: Terminal formatting
- `textual>=0.45.0`: Terminal UI framework
- `aiohttp>=3.8.0`: Async HTTP client

### System Dependencies
- Network tools: `atftp`, `iputils-arping`, `iproute2`
- Serial tools: `picocom`, `screen`, `minicom`
- Python: `python3-venv`, `python3-full`

## Key Patterns

### Router Management
- All router operations go through `OpenWrtManager` class
- Uses SSH with paramiko for command execution
- RouterConfig dataclass handles connection parameters
- Commands return structured results with stdout/stderr

### AI Integration
- Natural language commands parsed via Anthropic API
- JSON command format: `{"command": "packages", "action": "install", "package": "htop"}`
- Conversation history maintained for context
- Error handling and retry logic for failed commands

### Recovery Operations
- TFTP recovery requires network interface management
- Serial monitoring auto-detects CP2102 devices
- Recovery scripts include comprehensive user guidance
- Hardware-specific timings for WNDR3700 recovery mode

## File Structure Notes

- `bin/`: Contains generated wrapper scripts
- `firmware/`: Stores firmware images for recovery
- `logs/`: Application logs with timestamps
- All wrapper scripts automatically activate the venv
- Recovery tools require root privileges for network/hardware access