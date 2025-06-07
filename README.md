# 🛠️ RouterTools

> Router recovery toolkit for WNDR3700 with automated TFTP firmware flashing and serial U-Boot access.

## ✨ Features

- 🔧 **Automated TFTP Recovery** - One-click firmware flashing with intelligent retry logic
- 📡 **Network Auto-Detection** - Automatically finds and configures USB-to-Ethernet adapters  
- 🔍 **Firmware Validation** - Checks file integrity and compatibility before flashing
- 📺 **Serial Monitoring** - Real-time U-Boot console access and recovery guidance
- 🛡️ **Error Recovery** - Automatic cleanup and network configuration restoration

## 🚀 Quick Start

### Prerequisites
```bash
# Install required packages
sudo apt-get install atftp iputils-arping iproute2 picocom
```

### Recovery Process

1. **Put router in recovery mode:**
   - Power off router
   - Hold reset button  
   - Power on while holding reset
   - Wait for blinking power LED
   - Release reset button

2. **Run TFTP recovery:**
   ```bash
   sudo ./router-firmware.sh
   ```

3. **Optional - Monitor via serial:**
   ```bash
   sudo ./router-recovery-mode.sh
   ```

## 📁 Files

| File | Description |
|------|-------------|
| `router-firmware.sh` | Main TFTP recovery script with network configuration |
| `router-recovery-mode.sh` | Serial monitoring and U-Boot command guidance |
| `firmware.img` | Binary firmware file for WNDR3700 (6.6MB) |

## 🔌 Hardware Setup

### TFTP Recovery (Required)
- USB-to-Ethernet adapter
- Ethernet cable to router

### Serial Access (Optional)
- CP2102 USB-to-UART bridge
- Connect to router's serial pins:
  - **TX** (Pin 2) → **RX** (Adapter)
  - **RX** (Pin 3) → **TX** (Adapter)  
  - **GND** (Pin 4) → **GND** (Adapter)
  - ⚠️ **DO NOT** connect 3.3V (Pin 1)

## ⚙️ How It Works

1. **Detection** - Auto-detects network interfaces and USB adapters
2. **Configuration** - Sets up host as `192.168.1.2`, targets router at `192.168.1.1`
3. **Validation** - Checks firmware size (4-16MB) and binary signatures
4. **Transfer** - TFTP upload with timeout handling and retry logic
5. **Recovery** - Router flashes firmware automatically (3-5 minutes)

## 🎯 Supported Models

- **WNDR3700v2** (Primary target)
- Other WNDR3700 variants (may work)

## ⚠️ Important Notes

- **Root privileges required** for network configuration
- **Never power off** router during firmware flashing
- Scripts automatically restore network settings
- Recovery indicated by **blinking power LED**

## 📋 U-Boot Commands

If you have serial access, these commands can help:

```bash
tftpserver                    # Start TFTP recovery
setenv ipaddr 192.168.1.1     # Set router IP
setenv serverip 192.168.1.2   # Set computer IP
reset                         # Restart router
```

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| No network interfaces | Check USB adapter and install drivers |
| TFTP timeout | Verify router is in recovery mode (blinking LED) |
| Permission denied | Run scripts with `sudo` |
| Transfer fails | Check ethernet cable and firewall settings |

## 📄 License

This project is open source. Use at your own risk.

---

*Built for recovering bricked routers and restoring connectivity* 🌐