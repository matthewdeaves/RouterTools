# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a router recovery toolkit specifically designed for WNDR3700 routers. The repository contains scripts and firmware for recovering bricked routers using TFTP and serial communication methods.

## Core Components

- `router-firmware.sh` - Main TFTP-based recovery script with comprehensive error handling, network configuration, and firmware validation
- `router-recovery-mode.sh` - Serial monitoring script for U-Boot interaction and manual recovery guidance  
- `firmware.img` - Binary firmware file (6.6MB) for flashing to the router

## Key Architecture

The scripts follow a modular approach with distinct phases:

### router-firmware.sh
- **Network Detection**: Auto-detects USB-to-Ethernet adapters and configures interfaces
- **Firmware Validation**: Checks file size, binary format, and firmware signatures (HDR0, TRX, OWRT)
- **TFTP Recovery**: Implements retry logic with timeout handling and progress monitoring
- **Error Recovery**: Automatic network configuration restoration and cleanup

### router-recovery-mode.sh  
- **Serial Detection**: Auto-detects CP2102 USB-to-UART bridges
- **Tool Management**: Supports screen, picocom, and minicom with automatic installation
- **Recovery Guidance**: Provides U-Boot command sequences and hardware recovery instructions

## Usage Commands

### Running Recovery Scripts
```bash
# Main TFTP recovery (requires root)
sudo ./router-firmware.sh

# Serial monitoring and U-Boot access
sudo ./router-recovery-mode.sh
```

### Required Dependencies
```bash
# For TFTP recovery
sudo apt-get install atftp iputils-arping iproute2

# For serial monitoring  
sudo apt-get install picocom  # or screen/minicom
```

## Recovery Process Flow

1. **Hardware Setup**: Connect USB-to-Ethernet and optionally CP2102 serial adapter
2. **Router Preparation**: Put WNDR3700 into recovery mode (hold reset, power on, wait for blinking LED)
3. **Network Configuration**: Script configures host as 192.168.1.2, targets 192.168.1.1
4. **Firmware Transfer**: TFTP upload with retry logic and timeout handling
5. **Flash Process**: Router automatically flashes firmware (3-5 minutes, do not power off)

## Important Notes

- Scripts require root privileges for network configuration
- Firmware validation checks file size (4-16MB) and binary signatures
- Network configuration is automatically restored after completion
- Serial communication uses 115200 baud rate
- Recovery mode indicated by blinking power LED on router