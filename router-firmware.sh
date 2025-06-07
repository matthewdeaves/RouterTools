#!/bin/bash

# Router Recovery Script for WNDR3700
# This script automates the process of recovering a bricked WNDR3700 router

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

# Function to validate firmware file
validate_firmware() {
    local firmware_file="$1"
    
    echo -e "${BLUE}Validating firmware file...${NC}"
    
    # Check file size (should be reasonable for WNDR3700v2)
    local file_size=$(stat -c%s "$firmware_file" 2>/dev/null)
    if [ -z "$file_size" ]; then
        echo -e "${RED}Cannot read firmware file size${NC}"
        return 1
    fi
    
    # WNDR3700v2 firmware should be between 4MB and 16MB
    if [ "$file_size" -lt 4194304 ] || [ "$file_size" -gt 16777216 ]; then
        echo -e "${RED}Warning: Firmware size ($((file_size / 1024 / 1024))MB) outside expected range (4-16MB)${NC}"
        echo -e "${YELLOW}Continue anyway? (y/n)${NC}"
        read -r continue_anyway
        if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    # Check if it's a binary file
    if file "$firmware_file" | grep -q "text"; then
        echo -e "${RED}Warning: Firmware appears to be a text file, not binary${NC}"
        echo -e "${YELLOW}Continue anyway? (y/n)${NC}"
        read -r continue_anyway
        if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    # Look for common firmware headers/signatures
    local file_header=$(hexdump -C "$firmware_file" 2>/dev/null | head -n 5)
    if echo "$file_header" | grep -qE "(HDR0|.TRX|OWRT)"; then
        echo -e "${GREEN}Firmware signature detected - looks valid${NC}"
    else
        echo -e "${YELLOW}No recognized firmware signature found${NC}"
        echo -e "${YELLOW}This might not be a valid firmware file${NC}"
        echo -e "${YELLOW}Continue anyway? (y/n)${NC}"
        read -r continue_anyway
        if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    echo -e "${GREEN}Firmware validation complete${NC}"
    return 0
}

# Function to check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

# Function to setup USB-to-Ethernet adapter
setup_usb_ethernet() {
    echo -e "${BLUE}Setting up USB-to-Ethernet adapter...${NC}"
    
    # Check for USB network adapters
    echo -e "${YELLOW}Scanning for USB network adapters...${NC}"
    
    # List USB devices that might be network adapters
    if command_exists lsusb; then
        echo -e "${YELLOW}USB devices:${NC}"
        lsusb | grep -i -E "(network|ethernet|usb.*ethernet|realtek|asix)"
        
        # Check for kernel modules that might need loading
        echo -e "${YELLOW}Checking USB network adapter kernel modules...${NC}"
        local usb_modules="usbnet asix ax88179_178a r8152 cdc_ether"
        for module in $usb_modules; do
            if lsmod | grep -q "$module"; then
                echo -e "${GREEN}Module $module is loaded${NC}"
            else
                echo -e "${YELLOW}Loading module: $module${NC}"
                modprobe "$module" 2>/dev/null || true
            fi
        done
        
        # Wait for interface to appear
        echo -e "${YELLOW}Waiting for USB adapter to initialize...${NC}"
        sleep 3
    fi
    
    # Trigger udev to detect new devices
    if command_exists udevadm; then
        echo -e "${YELLOW}Triggering device detection...${NC}"
        udevadm trigger --subsystem-match=net
        udevadm settle
        sleep 2
    fi
}

# Function to detect Ethernet interfaces
detect_interfaces() {
    echo -e "${BLUE}Detecting Ethernet interfaces...${NC}"
    
    # Setup USB adapters first
    setup_usb_ethernet
    
    # Get all interfaces that are likely Ethernet (not wireless, loopback, etc.)
    interfaces=$(ip link show | grep -E '^[0-9]+: (e|en|eth)' | cut -d: -f2 | tr -d ' ')
    
    if [ -z "$interfaces" ]; then
        echo -e "${RED}No Ethernet interfaces detected!${NC}"
        echo -e "${YELLOW}Trying to detect USB adapters...${NC}"
        
        # Try to find any network interfaces
        all_interfaces=$(ip link show | grep -E '^[0-9]+:' | grep -v lo | cut -d: -f2 | tr -d ' ')
        if [ -n "$all_interfaces" ]; then
            echo -e "${YELLOW}Found these network interfaces:${NC}"
            for iface in $all_interfaces; do
                echo -e "- $iface"
            done
            interfaces="$all_interfaces"
        else
            echo -e "${RED}No network interfaces found at all!${NC}"
            exit 1
        fi
    fi
    
    # Display available interfaces
    echo -e "${YELLOW}Available network interfaces:${NC}"
    i=1
    for iface in $interfaces; do
        status=$(ip link show dev $iface | grep -o "state [A-Z]*" | cut -d ' ' -f2)
        # Check if it's a USB adapter
        usb_info=""
        if [ -d "/sys/class/net/$iface/device" ]; then
            if readlink "/sys/class/net/$iface/device" | grep -q usb; then
                usb_info=" [USB]"
            fi
        fi
        echo -e "$i) $iface (Status: $status)$usb_info"
        i=$((i+1))
    done
    
    # Let user select interface
    echo -e "${YELLOW}Enter the number of the interface to use:${NC}"
    read -r selection
    
    # Convert selection to interface name
    i=1
    for iface in $interfaces; do
        if [ "$i" -eq "$selection" ]; then
            INTERFACE=$iface
            break
        fi
        i=$((i+1))
    done
    
    if [ -z "$INTERFACE" ]; then
        echo -e "${RED}Invalid selection!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Selected interface: $INTERFACE${NC}"
}

# Function to configure network
configure_network() {
    echo -e "${BLUE}Configuring network interface $INTERFACE...${NC}"
    
    # Store original network configuration for restoration
    ORIGINAL_NM_STATE=""
    if command_exists systemctl && systemctl is-active --quiet NetworkManager; then
        ORIGINAL_NM_STATE="active"
        echo -e "${YELLOW}Stopping NetworkManager...${NC}"
        systemctl stop NetworkManager
        sleep 1
    fi
    
    # Store original interface configuration
    ORIGINAL_IP=$(ip addr show dev "$INTERFACE" 2>/dev/null | grep "inet " | awk '{print $2}' | head -n1)
    
    # Configure interface with error checking
    echo -e "${YELLOW}Setting IP address to 192.168.1.2...${NC}"
    
    # Flush existing addresses
    if ! ip addr flush dev "$INTERFACE" 2>/dev/null; then
        echo -e "${RED}Warning: Could not flush existing IP addresses${NC}"
    fi
    
    # Add new IP address
    if ! ip addr add 192.168.1.2/24 dev "$INTERFACE" 2>/dev/null; then
        echo -e "${RED}Failed to set IP address on $INTERFACE${NC}"
        restore_network_config
        exit 1
    fi
    
    # Bring interface up
    if ! ip link set dev "$INTERFACE" up 2>/dev/null; then
        echo -e "${RED}Failed to bring up interface $INTERFACE${NC}"
        restore_network_config
        exit 1
    fi
    
    # Wait for interface to come up with timeout
    echo -e "${YELLOW}Waiting for interface to come up...${NC}"
    local timeout=10
    local count=0
    while [ $count -lt $timeout ]; do
        if ip link show dev "$INTERFACE" | grep -q "state UP"; then
            break
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo
    
    # Check if interface is up and configured
    if ! ip link show dev "$INTERFACE" | grep -q "state UP"; then
        echo -e "${RED}Interface $INTERFACE failed to come up${NC}"
        echo -e "${YELLOW}Current state:${NC}"
        ip link show dev "$INTERFACE"
        echo -e "${YELLOW}This may indicate a hardware problem${NC}"
        restore_network_config
        exit 1
    fi
    
    # Verify IP configuration
    local configured_ip=$(ip addr show dev "$INTERFACE" | grep "inet 192.168.1.2" | awk '{print $2}')
    if [ -z "$configured_ip" ]; then
        echo -e "${RED}Failed to configure IP address properly${NC}"
        restore_network_config
        exit 1
    fi
    
    # Test basic connectivity (ARP)
    echo -e "${YELLOW}Testing network layer connectivity...${NC}"
    if ! arping -c 1 -I "$INTERFACE" 192.168.1.1 >/dev/null 2>&1; then
        echo -e "${YELLOW}No ARP response from router (this is normal if router is in recovery mode)${NC}"
    else
        echo -e "${GREEN}Router responded to ARP${NC}"
    fi
    
    # Display IP configuration
    echo -e "${GREEN}Network configuration successful:${NC}"
    ip addr show dev "$INTERFACE" | grep inet
}

# Function to restore network configuration
restore_network_config() {
    echo -e "${YELLOW}Restoring original network configuration...${NC}"
    
    # Restore original IP if it existed
    if [ -n "$ORIGINAL_IP" ]; then
        echo -e "${YELLOW}Restoring original IP: $ORIGINAL_IP${NC}"
        ip addr flush dev "$INTERFACE" 2>/dev/null
        ip addr add "$ORIGINAL_IP" dev "$INTERFACE" 2>/dev/null
    fi
    
    # Restart NetworkManager if it was running
    if [ "$ORIGINAL_NM_STATE" = "active" ] && command_exists systemctl; then
        echo -e "${YELLOW}Restarting NetworkManager...${NC}"
        systemctl start NetworkManager
    fi
}

# Function to check router connectivity
check_router() {
    echo -e "${BLUE}Checking connectivity to router (192.168.1.1)...${NC}"
    
    if ping -c 1 -W 2 192.168.1.1 >/dev/null 2>&1; then
        echo -e "${GREEN}Router is reachable!${NC}"
        return 0
    else
        echo -e "${YELLOW}Router is not responding to ping.${NC}"
        echo -e "${YELLOW}This is normal if the router is in recovery mode.${NC}"
        echo -e "${YELLOW}Continuing with TFTP transfer...${NC}"
        return 1
    fi
}

# Function to transfer firmware via TFTP
transfer_firmware() {
    echo -e "${BLUE}Preparing to transfer firmware...${NC}"
    
    # Check if atftp is installed
    if ! command_exists atftp; then
        echo -e "${RED}Error: atftp is required but not installed.${NC}"
        echo -e "${YELLOW}Please install it with: sudo apt-get install atftp${NC}"
        exit 1
    fi
    
    # Use firmware.img from same directory if it exists, otherwise ask
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local default_firmware="$script_dir/firmware.img"
    
    if [ -z "$FIRMWARE_PATH" ]; then
        if [ -f "$default_firmware" ]; then
            FIRMWARE_PATH="$default_firmware"
            echo -e "${GREEN}Using firmware file: $FIRMWARE_PATH${NC}"
        else
            echo -e "${YELLOW}Enter the full path to the firmware.img file:${NC}"
            read -r FIRMWARE_PATH
        fi
    fi
    
    # Check if firmware file exists
    if [ ! -f "$FIRMWARE_PATH" ]; then
        echo -e "${RED}Firmware file not found: $FIRMWARE_PATH${NC}"
        exit 1
    fi
    
    # Get firmware file size
    FIRMWARE_SIZE=$(du -h "$FIRMWARE_PATH" | cut -f1)
    local file_size_bytes=$(stat -c%s "$FIRMWARE_PATH")
    
    echo -e "${GREEN}Firmware file: $FIRMWARE_PATH (Size: $FIRMWARE_SIZE)${NC}"
    echo -e "${YELLOW}Starting TFTP transfer to 192.168.1.1...${NC}"
    echo -e "${YELLOW}This may take multiple attempts. Press Ctrl+C to stop.${NC}"
    
    # Set maximum attempts based on file size (larger files may need more attempts)
    local max_attempts=30
    if [ "$file_size_bytes" -gt 8388608 ]; then  # > 8MB
        max_attempts=50
    fi
    
    # Create a temp script for timeout handling
    local timeout_script="/tmp/tftp_transfer_$$"
    cat > "$timeout_script" << 'EOF'
#!/bin/bash
timeout 120 atftp --verbose --option "timeout 3" --option "mode octet" --option "blksize 1428" --put --local-file "$1" 192.168.1.1
exit_code=$?
if [ $exit_code -eq 124 ]; then
    echo "TFTP transfer timed out after 120 seconds"
    exit 2
fi
exit $exit_code
EOF
    chmod +x "$timeout_script"
    
    # Try TFTP transfer in a loop
    attempt=1
    consecutive_failures=0
    while [ $attempt -le $max_attempts ]; do
        echo -e "${BLUE}Attempt $attempt/$max_attempts at $(date)${NC}"
        
        # Run TFTP with timeout
        if "$timeout_script" "$FIRMWARE_PATH"; then
            echo -e "${GREEN}Transfer successful!${NC}"
            echo -e "${GREEN}The router is now flashing the firmware.${NC}"
            echo -e "${GREEN}This process will take several minutes.${NC}"
            echo -e "${GREEN}DO NOT power off the router during this time.${NC}"
            echo -e "${GREEN}The router will reboot automatically when done.${NC}"
            rm -f "$timeout_script"
            return 0
        else
            exit_code=$?
            consecutive_failures=$((consecutive_failures + 1))
            
            if [ $exit_code -eq 2 ]; then
                echo -e "${RED}Transfer timed out. Router may not be in recovery mode.${NC}"
            else
                echo -e "${YELLOW}Transfer failed (exit code: $exit_code).${NC}"
            fi
            
            # If we have too many consecutive failures, suggest checking connection
            if [ $consecutive_failures -ge 5 ]; then
                echo -e "${RED}Multiple consecutive failures detected.${NC}"
                echo -e "${YELLOW}Please check:${NC}"
                echo -e "- Router is powered on and in recovery mode (blinking power LED)"
                echo -e "- Ethernet cable is connected properly"
                echo -e "- No firewall blocking TFTP traffic"
                echo -e ""
                echo -e "${YELLOW}Continue trying? (y/n)${NC}"
                read -r continue_trying
                if [[ ! $continue_trying =~ ^[Yy]$ ]]; then
                    echo -e "${RED}Transfer cancelled by user${NC}"
                    rm -f "$timeout_script"
                    exit 1
                fi
                consecutive_failures=0
            fi
            
            if [ $attempt -lt $max_attempts ]; then
                echo -e "${YELLOW}Retrying in 3 seconds...${NC}"
                sleep 3
            fi
            attempt=$((attempt+1))
        fi
    done
    
    echo -e "${RED}Failed to transfer firmware after $max_attempts attempts${NC}"
    echo -e "${YELLOW}Possible issues:${NC}"
    echo -e "- Router is not in recovery mode"
    echo -e "- Network configuration problem"
    echo -e "- Incompatible firmware file"
    echo -e "- Hardware failure"
    rm -f "$timeout_script"
    exit 1
}

# Function to provide post-transfer instructions
post_transfer() {
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}Firmware transfer complete!${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${YELLOW}What happens now:${NC}"
    echo -e "1. The router is flashing the firmware (takes 3-5 minutes)"
    echo -e "2. The router will reboot automatically when done"
    echo -e "3. After reboot, you can access the router at:"
    echo -e "   - OpenWrt: http://192.168.1.1"
    echo -e "   - Netgear: http://www.routerlogin.net or http://192.168.1.1"
    echo -e ""
    echo -e "${YELLOW}Important notes:${NC}"
    echo -e "- DO NOT power off the router during flashing"
    echo -e "- The power LED will change patterns during the process"
    echo -e "- If the router doesn't respond after 10 minutes, try power cycling it"
    echo -e ""
    echo -e "${GREEN}Restore original network configuration? (y/n)${NC}"
    read -r restore_config
    if [[ $restore_config =~ ^[Yy]$ ]]; then
        restore_network_config
        echo -e "${GREEN}Network configuration restored.${NC}"
    else
        echo -e "${YELLOW}Network configuration left as-is for router access${NC}"
    fi
}

# Function to handle script interruption
cleanup_on_exit() {
    echo -e "\n${YELLOW}Script interrupted. Cleaning up...${NC}"
    restore_network_config
    rm -f /tmp/tftp_transfer_*
    exit 1
}

# Function to attempt firmware backup
attempt_firmware_backup() {
    echo -e "${BLUE}Attempting to backup current firmware...${NC}"
    
    # Check if router is accessible on standard IP
    local router_ip="192.168.1.1"
    local backup_file="firmware_backup_$(date +%Y%m%d_%H%M%S).bin"
    
    echo -e "${YELLOW}Checking if router is accessible at $router_ip...${NC}"
    if ping -c 1 -W 2 $router_ip >/dev/null 2>&1; then
        echo -e "${GREEN}Router is accessible${NC}"
        
        # Try to access router's web interface or telnet
        echo -e "${YELLOW}Attempting to access router web interface...${NC}"
        if command_exists curl; then
            # Try to access the router's web interface
            local response=$(curl -s --connect-timeout 5 http://$router_ip/ | head -c 100)
            if [ -n "$response" ]; then
                echo -e "${GREEN}Router web interface is responding${NC}"
                echo -e "${YELLOW}Manual backup required:${NC}"
                echo -e "1. Open http://$router_ip in your browser"
                echo -e "2. Log into the router admin interface"
                echo -e "3. Look for 'Backup Settings' or 'Router Status'"
                echo -e "4. Download the current firmware if available"
                echo -e ""
                echo -e "${YELLOW}Press any key to continue with recovery process...${NC}"
                read -r
            else
                echo -e "${YELLOW}Router accessible but web interface not responding${NC}"
            fi
        else
            echo -e "${YELLOW}curl not available. Install curl for web interface testing${NC}"
        fi
    else
        echo -e "${YELLOW}Router not accessible at $router_ip${NC}"
        echo -e "${YELLOW}This is normal if the router is already bricked${NC}"
    fi
    
    echo -e "${YELLOW}Continuing with firmware recovery process...${NC}"
    sleep 2
}

# Main function
main() {
    # Set up signal handlers for cleanup
    trap cleanup_on_exit INT TERM
    
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}       WNDR3700 Router Recovery Tool              ${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${GREEN}Enhanced version with improved error handling${NC}"
    echo -e ""
    
    # Check if user wants to backup current firmware first
    echo -e "${YELLOW}Do you want to try backing up the current firmware first? (y/n)${NC}"
    echo -e "${YELLOW}(This requires the router to be responding normally)${NC}"
    read -r backup_choice
    if [[ $backup_choice =~ ^[Yy]$ ]]; then
        attempt_firmware_backup
    fi
    
    # Check if running as root
    check_root
    
    # Check for required tools
    echo -e "${BLUE}Checking system requirements...${NC}"
    if ! command_exists ip; then
        echo -e "${RED}Error: 'ip' command not found. Please install iproute2.${NC}"
        exit 1
    fi
    
    if ! command_exists arping; then
        echo -e "${YELLOW}Warning: 'arping' not found. Please install iputils-arping if needed.${NC}"
        echo -e "${YELLOW}Command: sudo apt-get install iputils-arping${NC}"
    fi
    
    # Use firmware.img from same directory if it exists, otherwise ask with validation
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local default_firmware="$script_dir/firmware.img"
    
    if [ -f "$default_firmware" ]; then
        FIRMWARE_PATH="$default_firmware"
        echo -e "${GREEN}Using firmware file: $FIRMWARE_PATH${NC}"
        
        # Validate the default firmware file
        if ! validate_firmware "$FIRMWARE_PATH"; then
            echo -e "${RED}Default firmware validation failed${NC}"
            FIRMWARE_PATH=""
        fi
    fi
    
    # If no valid default firmware, ask for path with validation
    if [ -z "$FIRMWARE_PATH" ]; then
        while true; do
            echo -e "${YELLOW}Enter the full path to the firmware.img file:${NC}"
            read -r FIRMWARE_PATH
            
            # Allow relative paths by converting to absolute
            if [[ ! "$FIRMWARE_PATH" = /* ]]; then
                FIRMWARE_PATH="$(pwd)/$FIRMWARE_PATH"
            fi
            
            # Check if firmware file exists
            if [ ! -f "$FIRMWARE_PATH" ]; then
                echo -e "${RED}Firmware file not found: $FIRMWARE_PATH${NC}"
                echo -e "${YELLOW}Please enter a valid path or press Ctrl+C to exit${NC}"
                continue
            fi
            
            # Validate firmware file
            if validate_firmware "$FIRMWARE_PATH"; then
                break
            else
                echo -e "${RED}Firmware validation failed${NC}"
                echo -e "${YELLOW}Try a different file or press Ctrl+C to exit${NC}"
            fi
        done
    fi
    
    # Detect and select interface
    detect_interfaces
    
    # Configure network
    configure_network
    
    # Check router connectivity
    check_router
    
    # Final confirmation with detailed instructions
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}READY TO FLASH FIRMWARE${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${GREEN}Firmware file: $FIRMWARE_PATH${NC}"
    echo -e "${GREEN}Network interface: $INTERFACE${NC}"
    echo -e "${GREEN}Target IP: 192.168.1.1${NC}"
    echo -e ""
    echo -e "${YELLOW}IMPORTANT: Make sure the router is in recovery mode:${NC}"
    echo -e "1. Power off the router"
    echo -e "2. Hold the reset button"
    echo -e "3. Power on while holding reset"
    echo -e "4. Wait for power LED to blink green/amber"
    echo -e "5. Release the reset button"
    echo -e ""
    echo -e "${RED}WARNING: Do not power off the router during firmware flashing!${NC}"
    echo -e ""
    echo -e "${YELLOW}Continue with firmware transfer? (y/n)${NC}"
    read -r confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo -e "${RED}Operation cancelled by user.${NC}"
        restore_network_config
        exit 0
    fi
    
    # Transfer firmware
    transfer_firmware
    
    # Post-transfer instructions
    post_transfer
    
    echo -e "${GREEN}Router recovery process completed successfully!${NC}"
}

# Run the main function
main "$@"
