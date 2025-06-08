#!/bin/bash

# Router Serial Monitor Script
# This script monitors the serial output from the router and helps with recovery mode

# Text colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect and use the CP2102 USB-to-UART Bridge Controller
detect_cp2102() {
    echo -e "${BLUE}Detecting CP2102 USB-to-UART Bridge Controller...${NC}"
    
    # Check if the device exists
    if [ -e /dev/ttyUSB0 ]; then
        # Check if it's a CP2102
        if lsusb | grep -q "CP2102" || ls -l /dev/serial/by-id/ 2>/dev/null | grep -q "CP2102"; then
            echo -e "${GREEN}Found CP2102 USB-to-UART Bridge Controller at /dev/ttyUSB0${NC}"
            SERIAL_DEVICE="/dev/ttyUSB0"
            return 0
        fi
    fi
    
    # If we're here, we didn't find it at the default location, so search more broadly
    echo -e "${YELLOW}Searching for CP2102 device...${NC}"
    
    # Check by-id directory
    if [ -d /dev/serial/by-id ]; then
        CP2102_PATH=$(ls -l /dev/serial/by-id/ 2>/dev/null | grep -i "CP2102" | awk '{print $NF}' | head -n 1)
        if [ ! -z "$CP2102_PATH" ]; then
            SERIAL_DEVICE="/dev/serial/by-id/$(basename "$(dirname "$CP2102_PATH")")/$(basename "$CP2102_PATH")"
            echo -e "${GREEN}Found CP2102 device at $SERIAL_DEVICE${NC}"
            return 0
        fi
    fi
    
    # Check all ttyUSB devices
    for device in /dev/ttyUSB*; do
        if [ -e "$device" ]; then
            # Try to get device info
            if udevadm info -a -n "$device" 2>/dev/null | grep -i "CP2102" >/dev/null; then
                echo -e "${GREEN}Found CP2102 device at $device${NC}"
                SERIAL_DEVICE="$device"
                return 0
            fi
        fi
    done
    
    # If we're still here, we didn't find it
    echo -e "${RED}Could not automatically detect CP2102 device.${NC}"
    
    # List all potential serial devices
    echo -e "${YELLOW}All potential serial devices:${NC}"
    ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo -e "${RED}No USB serial devices found${NC}"
    
    # Ask for manual input
    echo -e "${YELLOW}Enter the serial device to use:${NC}"
    read -r SERIAL_DEVICE
    
    if [ -z "$SERIAL_DEVICE" ] || [ ! -e "$SERIAL_DEVICE" ]; then
        echo -e "${RED}Invalid or non-existent serial device!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Using serial device: $SERIAL_DEVICE${NC}"
    return 0
}

# Function to check required tools
check_tools() {
    echo -e "${BLUE}Checking required tools...${NC}"
    
    MISSING_TOOLS=0
    
    for tool in screen picocom minicom; do
        if command_exists $tool; then
            echo -e "${GREEN}Found: $tool${NC}"
            TOOL_TO_USE=$tool
            break
        else
            echo -e "${YELLOW}Not found: $tool${NC}"
            MISSING_TOOLS=$((MISSING_TOOLS + 1))
        fi
    done
    
    if [ $MISSING_TOOLS -eq 3 ]; then
        echo -e "${RED}No serial terminal program found.${NC}"
        echo -e "${YELLOW}This script requires root privileges to:${NC}"
        echo -e "- Install picocom serial terminal program"
        echo -e "- Set permissions on serial devices"
        echo -e ""
        echo -e "${BLUE}Please enter your password to install picocom:${NC}"
        sudo apt-get update
        sudo apt-get install -y picocom
        TOOL_TO_USE="picocom"
    fi
}

# Function to monitor serial output and provide guidance
monitor_serial() {
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}       Router Serial Monitor and Recovery Tool     ${NC}"
    echo -e "${BLUE}==================================================${NC}"
    
    echo -e "${YELLOW}This script will help you monitor the router's serial output${NC}"
    echo -e "${YELLOW}and guide you on when to press buttons for recovery mode.${NC}"
    echo -e ""
    echo -e "${GREEN}Instructions:${NC}"
    echo -e "1. Make sure your CP2102 adapter is connected to the router"
    echo -e "   - Router's TX (Pin 2) → USB adapter's RX"
    echo -e "   - Router's RX (Pin 3) → USB adapter's TX"
    echo -e "   - Router's GND (Pin 4) → USB adapter's GND"
    echo -e "   - DO NOT connect the 3.3V pin (Pin 1)"
    echo -e ""
    echo -e "2. Power on the router or press reset if it's already on"
    echo -e "3. Watch for boot messages"
    echo -e "4. Press any key when prompted to interrupt boot"
    echo -e "5. At the U-Boot prompt, you can enter commands"
    echo -e ""
    echo -e "${YELLOW}Common U-Boot commands for recovery:${NC}"
    echo -e "- tftpserver: Start TFTP recovery mode"
    echo -e "- setenv ipaddr 192.168.1.1: Set router IP"
    echo -e "- setenv serverip 192.168.1.2: Set your computer's IP"
    echo -e "- reset: Reboot the router"
    echo -e ""
    echo -e "${RED}To exit the serial monitor:${NC}"
    echo -e "- For screen: Press Ctrl+A then K"
    echo -e "- For picocom: Press Ctrl+A then Ctrl+X"
    echo -e "- For minicom: Press Ctrl+A then X"
    echo -e ""
    echo -e "${YELLOW}Starting serial monitor in 3 seconds...${NC}"
    sleep 3
    
    # Set permissions on serial device
    echo -e "${YELLOW}Setting permissions on serial device...${NC}"
    echo -e "${BLUE}Please enter your password to set serial device permissions:${NC}"
    sudo chmod a+rw $SERIAL_DEVICE
    
    # Start the appropriate serial terminal
    case $TOOL_TO_USE in
        screen)
            echo -e "${GREEN}Starting screen on $SERIAL_DEVICE at 115200 baud...${NC}"
            screen $SERIAL_DEVICE 115200
            ;;
        picocom)
            echo -e "${GREEN}Starting picocom on $SERIAL_DEVICE at 115200 baud...${NC}"
            picocom -b 115200 $SERIAL_DEVICE --omap crcrlf
            ;;
        minicom)
            echo -e "${GREEN}Starting minicom on $SERIAL_DEVICE at 115200 baud...${NC}"
            minicom -D $SERIAL_DEVICE -b 115200
            ;;
    esac
}

# Function to provide recovery instructions
show_recovery_instructions() {
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}       WNDR3700v2 Recovery Instructions           ${NC}"
    echo -e "${BLUE}==================================================${NC}"
    
    echo -e "${YELLOW}Hardware Recovery Mode (No Serial Required):${NC}"
    echo -e "1. Power off the router"
    echo -e "2. Hold the reset button"
    echo -e "3. Power on while holding reset"
    echo -e "4. Wait for power LED to blink green/amber (about 10-15 seconds)"
    echo -e "5. Release the reset button"
    echo -e "6. Router is now in TFTP recovery mode"
    echo -e "7. Run the router-firmware.sh script to upload firmware"
    echo -e ""
    
    echo -e "${YELLOW}If you see the U-Boot prompt (ar7100> or similar), try these commands:${NC}"
    echo -e ""
    echo -e "${GREEN}1. Start TFTP recovery mode:${NC}"
    echo -e "   tftpserver"
    echo -e ""
    echo -e "${GREEN}2. If that doesn't work, try:${NC}"
    echo -e "   setenv ipaddr 192.168.1.1"
    echo -e "   setenv serverip 192.168.1.2"
    echo -e "   tftpboot 0x80060000 firmware.img"
    echo -e ""
    echo -e "${GREEN}3. Manual flash commands (WNDR3700v2 specific):${NC}"
    echo -e "   tftpboot 0x80060000 firmware.img"
    echo -e "   erase 0xbf040000 +\$filesize"
    echo -e "   cp.b 0x80060000 0xbf040000 \$filesize"
    echo -e "   reset"
    echo -e ""
    echo -e "${GREEN}4. Backup current firmware (if working):${NC}"
    echo -e "   md.b 0xbf040000 0x7a0000 > /tmp/firmware_backup.hex"
    echo -e ""
    echo -e "${GREEN}5. Environment commands:${NC}"
    echo -e "   printenv          # Show all environment variables"
    echo -e "   saveenv           # Save environment to flash"
    echo -e "   reset             # Restart router"
    echo -e ""
    
    echo -e "${YELLOW}If you don't see the U-Boot prompt:${NC}"
    echo -e "1. Power cycle the router"
    echo -e "2. Press any key repeatedly during boot to interrupt"
    echo -e "3. Check serial connections:"
    echo -e "   - TX (Router Pin 2) → RX (Adapter)"  
    echo -e "   - RX (Router Pin 3) → TX (Adapter)"
    echo -e "   - GND (Router Pin 4) → GND (Adapter)"
    echo -e "   - DO NOT connect 3.3V (Pin 1)"
    echo -e "4. Try different baud rates: 115200, 57600, 38400"
    echo -e ""
    echo -e "${RED}Common Issues:${NC}"
    echo -e "- Crossed TX/RX connections"
    echo -e "- Wrong baud rate"
    echo -e "- Bad serial adapter"
    echo -e "- Router already bricked (try hardware recovery)"
    echo -e ""
    echo -e "${GREEN}Recovery Success Indicators:${NC}"
    echo -e "- Power LED changes from solid to blinking"
    echo -e "- Router responds to ping at 192.168.1.1"
    echo -e "- TFTP transfer starts successfully"
}

# Main function
main() {
    # Detect CP2102 device
    detect_cp2102
    
    # Check for required tools
    check_tools
    
    # Show recovery instructions
    show_recovery_instructions
    
    # Ask if user wants to continue
    echo -e "${YELLOW}Do you want to start monitoring the serial port? (y/n)${NC}"
    read -r confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo -e "${RED}Operation cancelled.${NC}"
        exit 0
    fi
    
    # Monitor serial
    monitor_serial
}

# Run the main function
main
