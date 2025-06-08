#!/usr/bin/env python3

import paramiko
import sys
import time
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import subprocess
import json

@dataclass
class RouterConfig:
    host: str = "192.168.1.1"
    username: str = "root"
    password: str = ""
    port: int = 22
    timeout: int = 30

class OpenWrtManager:
    def __init__(self, config: RouterConfig):
        self.config = config
        self.ssh_client = None
        self.connected = False
    
    def connect(self) -> bool:
        """Establish SSH connection to router"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.ssh_client.connect(
                hostname=self.config.host,
                username=self.config.username,
                password=self.config.password,
                port=self.config.port,
                timeout=self.config.timeout
            )
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"Failed to connect to router: {e}")
            return False
    
    def disconnect(self):
        """Close SSH connection"""
        if self.ssh_client:
            self.ssh_client.close()
            self.connected = False
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """Execute command on router and return stdout, stderr, exit_code"""
        if not self.connected:
            return "", "Not connected to router", 1
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            return stdout_data, stderr_data, exit_code
            
        except Exception as e:
            return "", f"Command execution failed: {e}", 1
    
    def get_system_info(self) -> Dict[str, str]:
        """Get basic system information"""
        commands = {
            'uptime': 'uptime',
            'memory': 'free -h',
            'storage': 'df -h',
            'kernel': 'uname -r',
            'openwrt_version': 'cat /etc/openwrt_release | grep DISTRIB_DESCRIPTION',
            'cpu_info': 'cat /proc/cpuinfo | grep "model name"'
        }
        
        info = {}
        for key, cmd in commands.items():
            stdout, stderr, exit_code = self.execute_command(cmd)
            if exit_code == 0:
                info[key] = stdout.strip()
            else:
                info[key] = f"Error: {stderr.strip()}"
        
        return info
    
    def update_packages(self) -> bool:
        """Update package lists"""
        print("Updating package lists...")
        stdout, stderr, exit_code = self.execute_command("opkg update", timeout=60)
        
        if exit_code == 0:
            print("Package lists updated successfully")
            return True
        else:
            print(f"Failed to update packages: {stderr}")
            return False
    
    def install_package(self, package_name: str) -> bool:
        """Install a package using opkg"""
        print(f"Installing package: {package_name}")
        stdout, stderr, exit_code = self.execute_command(f"opkg install {package_name}", timeout=120)
        
        if exit_code == 0:
            print(f"Successfully installed {package_name}")
            return True
        else:
            print(f"Failed to install {package_name}: {stderr}")
            return False
    
    def list_installed_packages(self) -> List[str]:
        """List all installed packages"""
        stdout, stderr, exit_code = self.execute_command("opkg list-installed")
        
        if exit_code == 0:
            packages = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    package_name = line.split()[0]
                    packages.append(package_name)
            return packages
        else:
            print(f"Failed to list packages: {stderr}")
            return []
    
    def setup_usb_storage(self, mount_point: str = "/mnt/usb") -> bool:
        """Setup USB storage for expanded storage"""
        commands = [
            "opkg update",
            "opkg install block-mount kmod-fs-ext4 kmod-usb-storage e2fsprogs",
            f"mkdir -p {mount_point}",
            "block detect > /etc/config/fstab",
            f"uci set fstab.@mount[0].target='{mount_point}'",
            "uci set fstab.@mount[0].enabled='1'",
            "uci commit fstab",
            "/etc/init.d/fstab enable",
            "/etc/init.d/fstab start"
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            stdout, stderr, exit_code = self.execute_command(cmd, timeout=60)
            if exit_code != 0:
                print(f"Command failed: {stderr}")
                return False
        
        print("USB storage setup completed")
        return True
    
    def setup_nordvpn(self) -> bool:
        """Setup NordVPN client"""
        nordvpn_packages = [
            "openvpn-openssl",
            "luci-app-openvpn",
            "wget",
            "unzip"
        ]
        
        print("Installing NordVPN dependencies...")
        if not self.update_packages():
            return False
        
        for package in nordvpn_packages:
            if not self.install_package(package):
                return False
        
        print("Creating NordVPN configuration directory...")
        self.execute_command("mkdir -p /etc/openvpn/nordvpn")
        
        print("NordVPN base setup completed. Manual configuration required:")
        print("1. Download NordVPN OpenVPN configs from nordvpn.com")
        print("2. Upload .ovpn files to /etc/openvpn/nordvpn/")
        print("3. Configure credentials in /etc/openvpn/nordvpn/auth.txt")
        print("4. Enable OpenVPN service: /etc/init.d/openvpn enable && /etc/init.d/openvpn start")
        
        return True
    
    def get_usb_devices(self) -> List[str]:
        """List USB devices"""
        stdout, stderr, exit_code = self.execute_command("lsusb")
        if exit_code == 0:
            return stdout.strip().split('\n')
        return []
    
    def get_storage_info(self) -> Dict[str, str]:
        """Get detailed storage information"""
        commands = {
            'disk_usage': 'df -h',
            'block_devices': 'lsblk',
            'mount_points': 'mount | grep -E "^/dev"'
        }
        
        info = {}
        for key, cmd in commands.items():
            stdout, stderr, exit_code = self.execute_command(cmd)
            if exit_code == 0:
                info[key] = stdout.strip()
            else:
                info[key] = f"Error: {stderr.strip()}"
        
        return info