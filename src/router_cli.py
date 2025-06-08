#!/usr/bin/env python3

import argparse
import sys
import os
import getpass
from router_manager import OpenWrtManager, RouterConfig
from anthropic_assistant import AnthropicRouterAssistant, create_assistant_from_env

def main():
    parser = argparse.ArgumentParser(description="OpenWrt Router Management Tool with Anthropic AI Assistant")
    
    parser.add_argument('--host', default='192.168.1.1', help='Router IP address')
    parser.add_argument('--user', default='root', help='SSH username')
    parser.add_argument('--password', default='', help='SSH password')
    parser.add_argument('--port', type=int, default=22, help='SSH port')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Get system information')
    
    # Package commands
    pkg_parser = subparsers.add_parser('packages', help='Package management')
    pkg_subparsers = pkg_parser.add_subparsers(dest='pkg_action')
    
    pkg_subparsers.add_parser('update', help='Update package lists')
    pkg_subparsers.add_parser('list', help='List installed packages')
    
    install_parser = pkg_subparsers.add_parser('install', help='Install package')
    install_parser.add_argument('package', help='Package name to install')
    
    # Storage commands
    storage_parser = subparsers.add_parser('storage', help='Storage management')
    storage_subparsers = storage_parser.add_subparsers(dest='storage_action')
    
    storage_subparsers.add_parser('info', help='Get storage information')
    storage_subparsers.add_parser('setup-usb', help='Setup USB storage')
    storage_subparsers.add_parser('usb-devices', help='List USB devices')
    
    # VPN commands
    vpn_parser = subparsers.add_parser('vpn', help='VPN management')
    vpn_subparsers = vpn_parser.add_subparsers(dest='vpn_action')
    vpn_subparsers.add_parser('setup-nordvpn', help='Setup NordVPN')
    
    # Command execution
    exec_parser = subparsers.add_parser('exec', help='Execute command on router')
    exec_parser.add_argument('command', nargs='+', help='Command to execute')
    
    # AI Assistant
    ai_parser = subparsers.add_parser('ai', help='Interactive AI assistant')
    ai_parser.add_argument('--message', help='Single message to AI assistant')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Prompt for password if not provided
    password = args.password
    if not password:
        try:
            password = getpass.getpass(f"SSH password for {args.user}@{args.host}: ")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return 1
    
    # Create router config
    config = RouterConfig(
        host=args.host,
        username=args.user,
        password=password,
        port=args.port
    )
    
    # Handle AI assistant
    if args.command == 'ai':
        assistant = create_assistant_from_env()
        if not assistant:
            return 1
        
        assistant.router_manager.config = config
        
        if args.message:
            # Single message mode
            if not assistant.connect_to_router():
                print("Failed to connect to router")
                return 1
            
            try:
                response = assistant.process_command_request(args.message)
                print(response)
            finally:
                assistant.disconnect_from_router()
        else:
            # Interactive mode
            assistant.interactive_session()
        
        return 0
    
    # Handle regular commands
    router = OpenWrtManager(config)
    
    if not router.connect():
        print("Failed to connect to router")
        return 1
    
    try:
        if args.command == 'info':
            info = router.get_system_info()
            for key, value in info.items():
                print(f"{key.title()}: {value}")
        
        elif args.command == 'packages':
            if args.pkg_action == 'update':
                router.update_packages()
            elif args.pkg_action == 'list':
                packages = router.list_installed_packages()
                for pkg in packages:
                    print(pkg)
            elif args.pkg_action == 'install':
                router.install_package(args.package)
            else:
                pkg_parser.print_help()
        
        elif args.command == 'storage':
            if args.storage_action == 'info':
                info = router.get_storage_info()
                for key, value in info.items():
                    print(f"\n{key.upper()}:")
                    print(value)
            elif args.storage_action == 'setup-usb':
                router.setup_usb_storage()
            elif args.storage_action == 'usb-devices':
                devices = router.get_usb_devices()
                for device in devices:
                    print(device)
            else:
                storage_parser.print_help()
        
        elif args.command == 'vpn':
            if args.vpn_action == 'setup-nordvpn':
                router.setup_nordvpn()
            else:
                vpn_parser.print_help()
        
        elif args.command == 'exec':
            command = ' '.join(args.command)
            stdout, stderr, exit_code = router.execute_command(command)
            if stdout:
                print("STDOUT:", stdout)
            if stderr:
                print("STDERR:", stderr)
            print(f"Exit code: {exit_code}")
            return exit_code
        
    finally:
        router.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())