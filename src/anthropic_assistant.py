#!/usr/bin/env python3

import os
import json
import requests
import getpass
import readline
import atexit
from typing import Dict, List, Any, Optional
from router_manager import OpenWrtManager, RouterConfig

class AnthropicRouterAssistant:
    def __init__(self, api_key: str, router_config: RouterConfig):
        self.api_key = api_key
        self.router_manager = OpenWrtManager(router_config)
        self.conversation_history = []
        self.base_url = "https://api.anthropic.com/v1/messages"
        
        self.system_prompt = """You are an OpenWrt router management assistant with full SSH root access.

IMPORTANT: Always execute commands FIRST, then interpret the results and respond to the user.

When users ask questions:
1. Start by running commands to gather information
2. Look at the actual output from the router
3. Give intelligent answers based on what you actually see

To execute commands, use this JSON format:
{"cmd": "command"}

For OpenWrt routers, use these commands instead of standard Linux ones:
- Instead of "lsblk" → use "ls /dev/sd* /dev/mmc*" or "cat /proc/partitions"
- Instead of "systemctl" → use "/etc/init.d/service_name"
- Use "logread" instead of "journalctl"
- Use "uci show" for configuration
- Use "opkg" for package management

ALWAYS execute commands first, see the results, then respond intelligently based on what you actually found."""

    def connect_to_router(self) -> bool:
        """Connect to the router"""
        return self.router_manager.connect()
    
    def disconnect_from_router(self):
        """Disconnect from router"""
        self.router_manager.disconnect()
    
    def execute_router_function(self, function_name: str, *args, **kwargs) -> Any:
        """Execute a router management function"""
        if not hasattr(self.router_manager, function_name):
            return f"Function {function_name} not available"
        
        try:
            func = getattr(self.router_manager, function_name)
            return func(*args, **kwargs)
        except Exception as e:
            return f"Error executing {function_name}: {e}"
    
    def send_message_to_anthropic(self, user_message: str) -> str:
        """Send message to Anthropic API and get response"""
        
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "system": self.system_prompt,
            "messages": self.conversation_history
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            
            response_data = response.json()
            assistant_message = response_data["content"][0]["text"]
            
            self.conversation_history.append({
                "role": "assistant", 
                "content": assistant_message
            })
            
            return assistant_message
            
        except requests.exceptions.RequestException as e:
            return f"API request failed: {e}"
        except KeyError as e:
            return f"Unexpected API response format: {e}"
    
    def process_command_request(self, user_input: str) -> str:
        """Process user request and execute router commands via AI"""
        
        # Send initial request to AI to get commands
        response = self.send_message_to_anthropic(user_input)
        
        # Parse and execute JSON commands from AI response
        import re
        json_pattern = r'\{[^{}]*"cmd"[^{}]*\}'
        json_commands = re.findall(json_pattern, response)
        
        # Execute all commands and collect results
        command_results = []
        for json_str in json_commands:
            try:
                command = json.loads(json_str)
                if 'cmd' in command:
                    cmd = command['cmd']
                    
                    print(f"\n\033[94m🤖 Executing:\033[0m \033[96m{cmd}\033[0m")
                    
                    # Execute the command via SSH
                    stdout, stderr, exit_code = self.router_manager.execute_command(cmd)
                    
                    # Store structured results
                    result = {
                        'command': cmd,
                        'success': exit_code == 0,
                        'stdout': stdout.strip(),
                        'stderr': stderr.strip(),
                        'exit_code': exit_code
                    }
                    command_results.append(result)
                        
            except json.JSONDecodeError as e:
                command_results.append({
                    'command': json_str,
                    'success': False,
                    'stdout': '',
                    'stderr': f'JSON parse error: {e}',
                    'exit_code': -1
                })
        
        # If we executed commands, send results back to AI for interpretation
        if command_results:
            results_summary = "Command execution results:\n"
            for result in command_results:
                results_summary += f"Command: {result['command']}\n"
                results_summary += f"Success: {result['success']}\n"
                if result['stdout']:
                    results_summary += f"Output: {result['stdout']}\n"
                if result['stderr']:
                    results_summary += f"Error: {result['stderr']}\n"
                results_summary += "---\n"
            
            # Send results back to AI for interpretation
            interpretation_prompt = f"Based on these command results, please answer the user's question: '{user_input}'\n\n{results_summary}"
            final_response = self.send_message_to_anthropic(interpretation_prompt)
            
            # Show execution details
            execution_details = "\n\n" + "\033[90m" + "="*50 + "\033[0m\n"
            execution_details += "\033[1mCOMMAND EXECUTION RESULTS:\033[0m\n"
            for result in command_results:
                if result['success']:
                    execution_details += f"\033[92m✅ Command succeeded:\033[0m \033[96m{result['command']}\033[0m\n"
                    if result['stdout']:
                        execution_details += f"\033[93m📋 Output:\033[0m\n\033[37m{result['stdout']}\033[0m\n"
                else:
                    execution_details += f"\033[91m❌ Command failed:\033[0m \033[96m{result['command']}\033[0m\n"
                    if result['stderr']:
                        execution_details += f"\033[91m🚨 Error:\033[0m \033[37m{result['stderr']}\033[0m\n"
            
            return final_response + execution_details
        
        return response
    
    def setup_readline(self):
        """Setup readline for command history and autocomplete"""
        history_file = os.path.expanduser('~/.router_ai_history')
        
        # Load history if it exists
        try:
            readline.read_history_file(history_file)
        except FileNotFoundError:
            pass
        
        # Set up history length
        readline.set_history_length(1000)
        
        # Save history on exit
        atexit.register(readline.write_history_file, history_file)
        
        # Basic tab completion for common commands
        def completer(text, state):
            commands = [
                'show system info', 'check memory usage', 'list packages',
                'show network config', 'check wifi status', 'show storage',
                'update packages', 'restart network', 'reboot router',
                'show logs', 'check cpu usage', 'show uptime'
            ]
            matches = [cmd for cmd in commands if cmd.startswith(text.lower())]
            if state < len(matches):
                return matches[state]
            return None
        
        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')
    
    def interactive_session(self):
        """Start an interactive session with the assistant"""
        print("\033[94mConnecting to router...\033[0m")
        if not self.connect_to_router():
            print("\033[91mFailed to connect to router. Exiting.\033[0m")
            return
        
        print("\033[92mConnected to router successfully!\033[0m")
        print("\033[93mStarting interactive session with Anthropic assistant...\033[0m")
        print("\033[90mType 'quit' or 'exit' to end the session. Use Tab for autocomplete.\033[0m")
        print("\033[90m" + "=" * 50 + "\033[0m")
        
        # Setup command history and autocomplete
        self.setup_readline()
        
        try:
            while True:
                user_input = input("\n\033[1mYou:\033[0m ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                
                if not user_input:
                    continue
                
                print("\n\033[1mA:\033[0m ", end="")
                print("\033[93m⏳ Processing...\033[0m", end="\r")
                response = self.process_command_request(user_input)
                print("\033[K", end="")  # Clear the processing line
                print(response)
                
        except KeyboardInterrupt:
            print("\n\n\033[93mSession interrupted by user.\033[0m")
        finally:
            self.disconnect_from_router()
            print("\033[90mDisconnected from router. Goodbye!\033[0m")

def create_assistant_from_env() -> Optional[AnthropicRouterAssistant]:
    """Create assistant using environment variables"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Please set ANTHROPIC_API_KEY environment variable")
        return None
    
    router_host = os.getenv('ROUTER_HOST', '192.168.1.1')
    router_user = os.getenv('ROUTER_USER', 'root')
    router_pass = os.getenv('ROUTER_PASS', '')
    
    # Prompt for password if not set in environment
    if not router_pass:
        try:
            router_pass = getpass.getpass(f"SSH password for {router_user}@{router_host}: ")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return None
    
    router_config = RouterConfig(
        host=router_host,
        username=router_user,
        password=router_pass
    )
    
    return AnthropicRouterAssistant(api_key, router_config)

if __name__ == "__main__":
    assistant = create_assistant_from_env()
    if assistant:
        assistant.interactive_session()