#!/usr/bin/env python3

import os
import json
import asyncio
import time
import getpass
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Input, RichLog, Static, Button, TabbedContent, TabPane
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from router_manager import OpenWrtManager, RouterConfig

class RouterAIApp(App):
    """A beautiful terminal-based router AI assistant"""
    
    TITLE = "🚀 Router AI Assistant"
    SUB_TITLE = "Powered by Claude AI ✨"
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+h", "help", "Help"),
        Binding("ctrl+r", "show_router_info", "Router Info"),
        Binding("ctrl+p", "show_packages", "Packages"),
        Binding("ctrl+m", "show_memory", "Memory"),
        Binding("ctrl+s", "save_chat", "Save Chat"),
        Binding("f1", "help", "Help"),
        Binding("ctrl+1", "switch_to_chat", "Chat Tab"),
        Binding("ctrl+2", "switch_to_commands", "Commands Tab"),
    ]
    
    CSS = """
    * {
        text-style: none;
    }
    
    Screen {
        layout: vertical;
        background: $surface;
    }
    
    Header {
        background: $primary;
        color: white;
        text-style: bold;
        height: 3;
    }
    
    Footer {
        background: $secondary;
        color: white;
        height: 1;
    }
    
    #menu_bar {
        height: 3;
        background: $accent;
        color: white;
        layout: horizontal;
        padding: 1;
    }
    
    .menu_button {
        height: 1;
        min-width: 12;
        margin: 0 1;
        background: $accent;
        color: white;
        border: none;
    }
    
    .menu_button:hover {
        background: $primary;
        text-style: bold;
    }
    
    #main_tabs {
        height: 1fr;
        background: $surface;
        margin: 0 1;
    }
    
    #chat_container {
        height: 1fr;
        background: $surface;
    }
    
    #commands_container {
        height: 1fr;
        background: $surface;
    }
    
    #chat_log {
        height: 1fr;
        width: 1fr;
        scrollbar-size: 1 1;
        background: $surface;
        margin: 1;
        border: solid $primary;
    }
    
    #commands_log {
        height: 1fr;
        width: 1fr;
        scrollbar-size: 1 1;
        background: $surface;
        margin: 1;
        border: solid $secondary;
    }
    
    TabbedContent {
        background: $surface;
    }
    
    TabPane {
        background: $surface;
        padding: 0;
    }
    
    Tabs {
        background: $accent;
    }
    
    Tab {
        background: $accent;
        color: white;
        text-style: bold;
        margin: 0 1;
    }
    
    Tab:hover {
        background: $primary;
    }
    
    Tab.-active {
        background: $primary;
        color: white;
        text-style: bold;
    }
    
    #input_container {
        height: 3;
        margin: 1;
    }
    
    #user_input {
        margin: 1;
        height: 1;
    }
    
    .status_bar {
        background: $primary;
        color: white;
        height: 1;
        content-align: center middle;
        text-style: bold;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.assistant = None
        self.router_manager = None
        self.is_processing = False
        self.message_count = 0
        self.current_input = ""
        self.thinking_animation = None
        self.thinking_frame = 0
        self.thinking_widget = None
        self.chat_history = []  # Store chat for copying
        self.session = None  # HTTP session for API calls
        
        # Configure logging
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(script_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up detailed logging (file only, no console output)
        log_file = os.path.join(self.log_dir, f"router_ai_{time.strftime('%Y%m%d_%H%M%S')}.log")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file)
            ]
        )
        self.logger = logging.getLogger("RouterAI")
        self.logger.info("Router AI UI starting up")
        
        self.logger.info(f"Log directory: {self.log_dir}")

    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield Header()
        
        # Menu bar
        with Container(id="menu_bar"):
            yield Button("📊 Info", id="menu_router_info", classes="menu_button")
            yield Button("📦 Pkgs", id="menu_packages", classes="menu_button")
            yield Button("💾 Mem", id="menu_memory", classes="menu_button")
            yield Button("🧹 Clear", id="menu_clear", classes="menu_button")
            yield Button("❓ Help", id="menu_help", classes="menu_button")
        
        # Tabbed interface
        with TabbedContent(id="main_tabs"):
            with TabPane("💬 Chat", id="chat_tab"):
                with Vertical(id="chat_container"):
                    yield RichLog(id="chat_log", markup=True)
            
            with TabPane("⚙️ Commands", id="commands_tab"):
                with Vertical(id="commands_container"):
                    yield RichLog(id="commands_log", markup=True)
        
        with Container(id="input_container"):
            yield Static(
                "Type your message... (Ctrl+Q to quit, Enter to send)",
                id="user_input"
            )
        
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app"""
        self.logger.info("on_mount called - initializing app")
        
        # Initialize HTTP session for async API calls
        timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        chat_log = self.query_one("#chat_log", RichLog)
        
        # Welcome message
        welcome = Panel(
            Align.center("🚀 Welcome to Router AI Assistant!\n\nConnecting to your router..."),
            title="[bold cyan]Welcome[/bold cyan]",
            border_style="cyan",
            expand=True,
            width=None
        )
        chat_log.write(welcome)
        
        # Initialize connection
        try:
            # Get connection details
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                chat_log.write("[red]❌ ANTHROPIC_API_KEY not set![/red]")
                return
            
            router_host = os.getenv('ROUTER_HOST', '192.168.1.1')
            router_user = os.getenv('ROUTER_USER', 'root')
            router_pass = os.getenv('ROUTER_PASS', '')
            
            if not router_pass:
                # This won't work in UI mode, so show error
                error_panel = Panel(
                    "❌ Router password not set!\n\nPlease set ROUTER_PASS environment variable\nor use the command line version.",
                    title="[bold red]Connection Error[/bold red]",
                    border_style="red",
                    expand=True,
                    width=None
                )
                chat_log.write(error_panel)
                return
            
            # Create router manager
            router_config = RouterConfig(
                host=router_host,
                username=router_user,
                password=router_pass
            )
            self.router_manager = OpenWrtManager(router_config)
            
            # Test connection
            try:
                connected = await asyncio.to_thread(self.router_manager.connect)
                if connected:
                    success_panel = Panel(
                        Align.center("✅ Connected to router successfully!\n\nReady to assist with your router!"),
                        title="[bold green]Connected[/bold green]",
                        border_style="green",
                        expand=True,
                        width=None
                    )
                    chat_log.write(success_panel)
                    
                    # Show help
                    help_panel = Panel(
                        "💡 Try asking:\n• 'show system info'\n• 'check memory usage'\n• 'list installed packages'\n\n📊 Quick Menu: Click buttons above for instant actions\n⌨️ Shortcuts: Ctrl+R (info), Ctrl+M (memory), Ctrl+P (packages)\n🎯 Press Ctrl+H for help, Ctrl+Q to quit",
                        title="[bold cyan]Quick Start[/bold cyan]",
                        border_style="cyan",
                        expand=True,
                        width=None
                    )
                    chat_log.write(help_panel)
                    
                    # Initialize AI assistant with connected router manager
                    self.assistant = UIAnthropicRouterAssistant(api_key, self.router_manager)
                    
                else:
                    error_panel = Panel(
                        f"❌ Failed to connect to router at {router_host}\n\nCheck your connection and credentials.",
                        title="[bold red]Connection Failed[/bold red]",
                        border_style="red",
                        expand=True,
                        width=None
                    )
                    chat_log.write(error_panel)
            except Exception as e:
                error_panel = Panel(
                    f"❌ Connection error: {str(e)[:100]}\n\nCheck router IP, credentials, and network.",
                    title="[bold red]Connection Error[/bold red]",
                    border_style="red",
                    expand=True,
                    width=None
                )
                chat_log.write(error_panel)
                
        except Exception as e:
            error_panel = Panel(
                f"❌ Error: {e}",
                title="[bold red]Error[/bold red]",
                border_style="red",
                expand=True,
                width=None
            )
            chat_log.write(error_panel)
        
        # Focus the input field (app gets focus for key events)
        try:
            self.logger.info("Setting up app focus for key events")
            self.focus()
            self.logger.info("App focus completed")
        except Exception as e:
            self.logger.error(f"Failed to setup app focus: {e}")

    async def on_key(self, event) -> None:
        """Handle key presses for custom text input"""
        if event.key == "enter":
            # Submit current input
            if self.is_processing:
                chat_log = self.query_one("#chat_log", RichLog)
                chat_log.write("[yellow]⏳ Please wait, already processing a command...[/yellow]")
                return
                
            if not self.assistant:
                chat_log = self.query_one("#chat_log", RichLog)
                chat_log.write("[red]❌ Not connected to router[/red]")
                return
                
            user_input = self.current_input.strip()
            if not user_input:
                return
            
            # Clear input and process message
            self.current_input = ""
            self.update_input_display()
            await self.process_message(user_input)
            
        elif event.key == "backspace":
            # Remove last character
            if self.current_input:
                self.current_input = self.current_input[:-1]
                self.update_input_display()
                
        elif event.key == "ctrl+c":
            # Clear input
            self.current_input = ""
            self.update_input_display()
            
        elif event.key == "ctrl+v":
            # Paste from clipboard
            try:
                import subprocess
                # Try to get clipboard content (works on most Linux systems)
                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    clipboard_text = result.stdout
                    # Handle multi-line paste - replace newlines with spaces for single-line input
                    cleaned_text = clipboard_text.replace('\n', ' ').replace('\r', ' ')
                    self.current_input += cleaned_text
                    self.update_input_display()
                else:
                    # Fallback: try xsel
                    result = subprocess.run(['xsel', '--clipboard'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        clipboard_text = result.stdout
                        cleaned_text = clipboard_text.replace('\n', ' ').replace('\r', ' ')
                        self.current_input += cleaned_text
                        self.update_input_display()
            except Exception as e:
                self.logger.error(f"Failed to paste from clipboard: {e}")
                # Show message to user
                chat_log = self.query_one("#chat_log", RichLog)
                chat_log.write("[yellow]⚠️ Paste failed - ensure xclip or xsel is installed[/yellow]")
            
        elif event.key == "space":
            # Add space character
            self.current_input += " "
            self.update_input_display()
            
        elif event.key == "period" or event.key == ".":
            # Add period
            self.current_input += "."
            self.update_input_display()
            
        elif event.key == "comma" or event.key == ",":
            # Add comma
            self.current_input += ","
            self.update_input_display()
            
        elif len(event.key) == 1 and event.key.isprintable():
            # Add character to input
            self.current_input += event.key
            self.update_input_display()

    def update_input_display(self):
        """Update the visual display of current input"""
        try:
            input_widget = self.query_one("#user_input", Static)
            if self.current_input:
                # Show current text with cursor
                display_text = f"> {self.current_input}█"
            else:
                # Show placeholder
                display_text = "Type your message... (Ctrl+Q to quit, Enter to send)"
            input_widget.update(display_text)
        except Exception as e:
            self.logger.error(f"Failed to update input display: {e}")

    def start_thinking_animation(self):
        """Start animated thinking indicator with progress animation"""
        try:
            chat_log = self.query_one("#chat_log", RichLog)
            
            # Show initial thinking message
            thinking_panel = Panel(
                "🤔 AI is thinking and executing commands...",
                title="[bold yellow]Processing[/bold yellow]",
                border_style="yellow",
                expand=True,
                width=None
            )
            chat_log.write(thinking_panel)
            
            # Start progress animation
            self.thinking_frame = 0
            if self.thinking_animation:
                self.thinking_animation.cancel()
            self.thinking_animation = self.set_interval(0.5, self.update_thinking_animation)
            
        except Exception as e:
            self.logger.error(f"Failed to start thinking animation: {e}")

    def stop_thinking_animation(self):
        """Stop thinking animation"""
        try:
            if self.thinking_animation:
                self.thinking_animation.cancel()
                self.thinking_animation = None
        except Exception as e:
            self.logger.error(f"Failed to stop thinking animation: {e}")

    def update_thinking_animation(self):
        """Update the thinking animation with a spinner"""
        try:
            chat_log = self.query_one("#chat_log", RichLog)
            
            # Animated spinner frames
            frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner = frames[self.thinking_frame % len(frames)]
            self.thinking_frame += 1
            
            # Update the last message with spinner
            progress_text = f"{spinner} AI is processing your request..."
            
            # Only update if we're still processing
            if self.is_processing:
                thinking_panel = Panel(
                    progress_text,
                    title="[bold yellow]Processing[/bold yellow]",
                    border_style="yellow",
                    expand=True,
                    width=None
                )
                # Remove the last thinking message and add updated one
                if hasattr(chat_log, '_lines') and chat_log._lines:
                    # Only update if the last message was a thinking message
                    pass  # Keep it simple to avoid UI issues
                    
        except Exception as e:
            self.logger.error(f"Failed to update thinking animation: {e}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if self.is_processing:
            return  # Prevent multiple commands running simultaneously
            
        button_id = event.button.id
        
        if button_id == "menu_router_info":
            await self.process_message("show system info")
        elif button_id == "menu_packages":
            await self.process_message("list installed packages")
        elif button_id == "menu_memory":
            await self.process_message("check memory usage")
        elif button_id == "menu_clear":
            self.action_clear_chat()
        elif button_id == "menu_help":
            self.action_help()

    async def process_message(self, user_input: str) -> None:
        """Process user message and get AI response"""
        self.is_processing = True
        self.message_count += 1
        
        chat_log = self.query_one("#chat_log", RichLog)
        commands_log = self.query_one("#commands_log", RichLog)
        
        try:
            # Show user message
            user_panel = Panel(
                Text(user_input, style="bold cyan"),
                title=f"[bold blue]You (#{self.message_count})[/bold blue]",
                border_style="blue",
                expand=True,
                width=None
            )
            chat_log.write(user_panel)
            
            # Store in chat history
            self.chat_history.append(f"You: {user_input}")
            
            # Start thinking animation
            self.start_thinking_animation()
            
            # Get AI response asynchronously
            response = await self.assistant.process_command_request_with_ui_async(
                user_input,
                self.log_command,
                self.session
            )
            
            # Stop thinking animation
            self.stop_thinking_animation()
            
            # Show AI response
            ai_panel = Panel(
                Text.from_markup(response),
                title="[bold green]🤖 AI Assistant[/bold green]",
                border_style="green",
                expand=True,
                width=None
            )
            chat_log.write(ai_panel)
            
            # Store in chat history (clean version without markup)
            clean_response = response.replace("[", "").replace("]", "").replace("/", "")
            self.chat_history.append(f"AI: {clean_response}")
            
        except Exception as e:
            self.stop_thinking_animation()
            chat_log.write(f"[red]❌ Error: {e}[/red]")
        finally:
            self.is_processing = False

    def log_command(self, command: str, success: bool, stdout: str, stderr: str) -> None:
        """Log command execution with safe output handling"""
        try:
            commands_log = self.query_one("#commands_log", RichLog)
            
            # Command header with more detailed status
            status = "✅ SUCCESS" if success else "❌ FAILED"
            color = "green" if success else "red"
            
            # Safely truncate command if too long
            safe_command = command[:100] + "..." if len(command) > 100 else command
            
            # Add summary of what happened
            summary = ""
            if success and stdout:
                if "installed" in stdout.lower():
                    summary = " (Package installed)"
                elif "removed" in stdout.lower():
                    summary = " (Package removed)"
                elif "updated" in stdout.lower():
                    summary = " (Updated successfully)"
                elif "started" in stdout.lower() or "running" in stdout.lower():
                    summary = " (Service started)"
                elif "stopped" in stdout.lower():
                    summary = " (Service stopped)"
                else:
                    summary = " (Completed)"
            elif not success:
                if "not found" in stderr.lower():
                    summary = " (Command/package not found)"
                elif "permission denied" in stderr.lower():
                    summary = " (Permission denied)"
                elif "connection" in stderr.lower():
                    summary = " (Connection error)"
                else:
                    summary = " (Command failed)"
            
            cmd_panel = Panel(
                Text(safe_command, style="bold cyan"),
                title=f"[{color}]{status}{summary}[/{color}]",
                border_style=color,
                expand=True,
                width=None
            )
            commands_log.write(cmd_panel)
            
            # Show output with better context
            if stdout:
                clean_stdout = stdout.strip()[:300]
                if len(stdout) > 300:
                    clean_stdout += "\n... (output truncated)"
                clean_stdout = ''.join(char for char in clean_stdout if ord(char) < 127 or char in '\n\t')
                commands_log.write(f"[green]✓ Output:[/green]\n{clean_stdout}")
            
            if stderr:
                clean_stderr = stderr.strip()[:200]
                if len(stderr) > 200:
                    clean_stderr += "\n... (error truncated)"
                clean_stderr = ''.join(char for char in clean_stderr if ord(char) < 127 or char in '\n\t')
                commands_log.write(f"[red]✗ Error:[/red]\n{clean_stderr}")
            
            # Show a clear result summary
            if success:
                commands_log.write("[green]→ Command completed successfully[/green]")
            else:
                commands_log.write("[red]→ Command failed - check error details above[/red]")
            
            commands_log.write("")  # Spacing
            
        except Exception as e:
            try:
                commands_log = self.query_one("#commands_log", RichLog)
                commands_log.write(f"[red]⚠️ Command log error: {str(e)[:100]}[/red]")
            except:
                pass

    def action_clear_chat(self) -> None:
        """Clear chat log"""
        chat_log = self.query_one("#chat_log", RichLog)
        chat_log.clear()
        chat_log.write("[cyan]💫 Chat cleared! Ready for new questions.[/cyan]")

    def action_help(self) -> None:
        """Show help"""
        chat_log = self.query_one("#chat_log", RichLog)
        help_text = """🤖 Router AI Assistant Help

💬 Chat Commands:
• Ask anything about your router in plain English
• Examples: "show system status", "check memory", "list packages"

📊 Quick Actions (Menu Bar):
• Router Info: System information and uptime
• Packages: Installed package list  
• Memory: Memory usage and statistics
• Clear: Clear chat history
• Help: Show this help

📑 Tabs:
• Chat Tab: Full-screen AI conversation
• Commands Tab: Full-screen command execution history
• Switch between tabs by clicking or using Ctrl+1/Ctrl+2

⌨️ Keyboard Shortcuts:
• Ctrl+Q: Quit application
• Ctrl+C: Clear input field
• Ctrl+V: Paste from clipboard (multi-line supported)
• Ctrl+S: Save chat to file
• Ctrl+1: Switch to Chat tab
• Ctrl+2: Switch to Commands tab
• Ctrl+R: Router info
• Ctrl+P: Package list
• Ctrl+M: Memory usage
• Ctrl+H / F1: Show help

🔧 Features:
• Tabbed interface with full-screen views
• AI-powered router management
• Natural language interface
• Menu buttons for quick access

✨ Powered by Claude AI and OpenWrt magic!"""
        
        help_panel = Panel(
            help_text,
            title="[bold cyan]📖 Help Guide[/bold cyan]",
            border_style="cyan",
            expand=True,
            width=None
        )
        chat_log.write(help_panel)

    def action_show_router_info(self) -> None:
        """Show router info shortcut"""
        if not self.is_processing:
            asyncio.create_task(self.process_message("show system info"))

    def action_show_packages(self) -> None:
        """Show packages shortcut"""
        if not self.is_processing:
            asyncio.create_task(self.process_message("list installed packages"))

    def action_show_memory(self) -> None:
        """Show memory shortcut"""
        if not self.is_processing:
            asyncio.create_task(self.process_message("check memory usage"))

    def action_switch_to_chat(self) -> None:
        """Switch to chat tab"""
        try:
            tabs = self.query_one("#main_tabs", TabbedContent)
            tabs.active = "chat_tab"
        except:
            pass

    def action_switch_to_commands(self) -> None:
        """Switch to commands tab"""
        try:
            tabs = self.query_one("#main_tabs", TabbedContent)
            tabs.active = "commands_tab"
        except:
            pass

    def action_save_chat(self) -> None:
        """Save chat history to file"""
        try:
            if not self.chat_history:
                chat_log = self.query_one("#chat_log", RichLog)
                chat_log.write("[yellow]No chat history to save yet[/yellow]")
                return
                
            # Save to file with timestamp
            import time
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"chat_history_{timestamp}.txt"
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(script_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Router AI Chat History\n")
                f.write("=" * 50 + "\n\n")
                for entry in self.chat_history:
                    f.write(f"{entry}\n\n")
            
            chat_log = self.query_one("#chat_log", RichLog)
            chat_log.write(f"[green]💾 Chat saved to: {filename}[/green]")
            
        except Exception as e:
            chat_log = self.query_one("#chat_log", RichLog)
            chat_log.write(f"[red]❌ Failed to save chat: {e}[/red]")


    async def on_unmount(self) -> None:
        """Cleanup on exit"""
        if self.router_manager:
            await asyncio.to_thread(self.router_manager.disconnect)
        
        # Close HTTP session
        if self.session:
            await self.session.close()

# Create the UI version of the assistant
class UIAnthropicRouterAssistant:
    def __init__(self, api_key: str, router_manager: OpenWrtManager):
        self.api_key = api_key
        self.router_manager = router_manager
        self.conversation_history = []
        self.base_url = "https://api.anthropic.com/v1/messages"
        
        self.system_prompt = """You are an OpenWrt router management assistant with SSH access.

Execute commands first, then interpret results and respond to the user.

To execute commands, use this JSON format:
{"cmd": "command"}

Use OpenWrt-specific commands:
- "uci show" for configuration
- "opkg" for packages  
- "logread" for logs
- "/etc/init.d/service_name" for services

CRITICAL: Always execute commands first, see results, then respond based on actual output.

IMPORTANT: Always clearly report whether commands succeeded or failed:
- If a command succeeds, say "✅ Successfully [what was done]"
- If a command fails, say "❌ Failed to [what was attempted]" and explain why
- Always summarize what actually happened, don't leave the user guessing
- If you install/configure something, confirm it's working
- If you make changes, verify they took effect"""

    async def send_message_to_anthropic_async(self, user_message: str, session: aiohttp.ClientSession) -> str:
        """Send message to Anthropic API asynchronously with conversation management"""
        
        self.conversation_history.append({
            "role": "user", 
            "content": user_message
        })
        
        # Limit conversation history to prevent memory issues
        # Keep only the last 10 messages (5 user + 5 assistant)
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
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
            async with session.post(self.base_url, headers=headers, json=data) as response:
                response.raise_for_status()
                response_data = await response.json()
                assistant_message = response_data["content"][0]["text"]
                
                # Truncate long messages to prevent memory bloat
                truncated_message = assistant_message[:2000] if len(assistant_message) > 2000 else assistant_message
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": truncated_message
                })
                
                return assistant_message
                
        except Exception as e:
            return f"API request failed: {str(e)[:200]}"

    def send_message_to_anthropic(self, user_message: str) -> str:
        """Synchronous wrapper for backwards compatibility"""
        import requests
        
        self.conversation_history.append({
            "role": "user", 
            "content": user_message
        })
        
        # Limit conversation history to prevent memory issues
        # Keep only the last 10 messages (5 user + 5 assistant)
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
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
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            response_data = response.json()
            assistant_message = response_data["content"][0]["text"]
            
            # Truncate long messages to prevent memory bloat
            truncated_message = assistant_message[:2000] if len(assistant_message) > 2000 else assistant_message
            
            self.conversation_history.append({
                "role": "assistant",
                "content": truncated_message
            })
            
            return assistant_message
            
        except Exception as e:
            return f"API request failed: {str(e)[:200]}"

    async def process_command_request_with_ui_async(self, user_input: str, command_callback, session: aiohttp.ClientSession) -> str:
        """Process request with UI command logging asynchronously"""
        import re
        
        # Get AI response asynchronously
        response = await self.send_message_to_anthropic_async(user_input, session)
        
        # Parse JSON commands
        json_pattern = r'\{[^{}]*"cmd"[^{}]*\}'
        json_commands = re.findall(json_pattern, response)
        
        # Limit number of commands to prevent UI overload
        if len(json_commands) > 5:
            json_commands = json_commands[:5]
        
        # Execute commands
        command_results = []
        for json_str in json_commands:
            try:
                command = json.loads(json_str)
                if 'cmd' in command:
                    cmd = command['cmd']
                    # Execute command in thread to avoid blocking
                    stdout, stderr, exit_code = await asyncio.to_thread(
                        self.router_manager.execute_command, cmd
                    )
                    
                    # Truncate outputs before logging to prevent UI issues
                    safe_stdout = stdout[:500] if stdout else ""
                    safe_stderr = stderr[:300] if stderr else ""
                    
                    # Log to UI with safe outputs
                    command_callback(cmd, exit_code == 0, safe_stdout, safe_stderr)
                    
                    # Store results with limited output for AI
                    result = {
                        'command': cmd,
                        'success': exit_code == 0,
                        'stdout': stdout.strip()[:1000],  # Limit for AI context
                        'stderr': stderr.strip()[:500],
                        'exit_code': exit_code
                    }
                    command_results.append(result)
                        
            except json.JSONDecodeError as e:
                command_callback(json_str, False, "", f"JSON parse error: {str(e)[:100]}")
            except Exception as e:
                command_callback("command_error", False, "", f"Execution error: {str(e)[:100]}")
        
        # Send results back to AI for interpretation
        if command_results:
            results_summary = "Command execution results:\n"
            for result in command_results:
                results_summary += f"Command: {result['command']}\n"
                results_summary += f"Success: {result['success']}\n"
                if result['stdout']:
                    results_summary += f"Output: {result['stdout'][:500]}...\n"  # Truncate for AI
                if result['stderr']:
                    results_summary += f"Error: {result['stderr'][:300]}...\n"
                results_summary += "---\n"
            
            # Limit the size of the interpretation prompt
            if len(results_summary) > 3000:
                results_summary = results_summary[:3000] + "\n... (results truncated)"
            
            interpretation_prompt = f"Based on these command results, answer: '{user_input}'\n\n{results_summary}"
            final_response = await self.send_message_to_anthropic_async(interpretation_prompt, session)
            return final_response
        
        return response

    def process_command_request_with_ui(self, user_input: str, command_callback) -> str:
        """Synchronous wrapper for backwards compatibility"""
        import re
        
        # Get AI response
        response = self.send_message_to_anthropic(user_input)
        
        # Parse JSON commands
        json_pattern = r'\{[^{}]*"cmd"[^{}]*\}'
        json_commands = re.findall(json_pattern, response)
        
        # Limit number of commands to prevent UI overload
        if len(json_commands) > 5:
            json_commands = json_commands[:5]
        
        # Execute commands
        command_results = []
        for json_str in json_commands:
            try:
                command = json.loads(json_str)
                if 'cmd' in command:
                    cmd = command['cmd']
                    stdout, stderr, exit_code = self.router_manager.execute_command(cmd)
                    
                    # Truncate outputs before logging to prevent UI issues
                    safe_stdout = stdout[:500] if stdout else ""
                    safe_stderr = stderr[:300] if stderr else ""
                    
                    # Log to UI with safe outputs
                    command_callback(cmd, exit_code == 0, safe_stdout, safe_stderr)
                    
                    # Store results with limited output for AI
                    result = {
                        'command': cmd,
                        'success': exit_code == 0,
                        'stdout': stdout.strip()[:1000],  # Limit for AI context
                        'stderr': stderr.strip()[:500],
                        'exit_code': exit_code
                    }
                    command_results.append(result)
                        
            except json.JSONDecodeError as e:
                command_callback(json_str, False, "", f"JSON parse error: {str(e)[:100]}")
            except Exception as e:
                command_callback("command_error", False, "", f"Execution error: {str(e)[:100]}")
        
        # Send results back to AI for interpretation
        if command_results:
            results_summary = "Command execution results:\n"
            for result in command_results:
                results_summary += f"Command: {result['command']}\n"
                results_summary += f"Success: {result['success']}\n"
                if result['stdout']:
                    results_summary += f"Output: {result['stdout'][:500]}...\n"  # Truncate for AI
                if result['stderr']:
                    results_summary += f"Error: {result['stderr'][:300]}...\n"
                results_summary += "---\n"
            
            # Limit the size of the interpretation prompt
            if len(results_summary) > 3000:
                results_summary = results_summary[:3000] + "\n... (results truncated)"
            
            interpretation_prompt = f"Based on these command results, answer: '{user_input}'\n\n{results_summary}"
            final_response = self.send_message_to_anthropic(interpretation_prompt)
            return final_response
        
        return response

def main():
    """Main entry point"""
    print("\n🚀 Starting Router AI Assistant...\n")
    
    # Check for required environment variables
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        print("💡 Example: export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    if not os.getenv('ROUTER_PASS'):
        print("❌ Please set ROUTER_PASS environment variable")
        print("💡 Example: export ROUTER_PASS='your-router-password'")
        print("💡 Or use: ROUTER_PASS='password' ./router-ai")
        return
    
    try:
        app = RouterAIApp()
        app.run()
    except KeyboardInterrupt:
        print("\n✨ Goodbye! Thanks for using Router AI Assistant!")
    except Exception as e:
        print(f"\n💥 Error: {e}")

if __name__ == "__main__":
    main()