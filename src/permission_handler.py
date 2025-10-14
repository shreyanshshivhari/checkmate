"""
Permission and Authorization Handler
Manages user consent and system access permissions
"""

import os
import sys
import platform
import yaml
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

class PermissionHandler:
    def __init__(self, config_path="config/settings.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        
    def _load_config(self):
        """Load configuration from YAML"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[red]Config file not found: {self.config_path}[/red]")
            sys.exit(1)
    
    def _save_config(self):
        """Save configuration to YAML"""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def check_admin_privileges(self):
        """Check if running with admin/root privileges"""
        if self.is_windows:
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                return False
        else:  # Linux/Unix
            return os.geteuid() == 0
    
    def request_elevation(self):
        """Request admin/root privileges"""
        console.print("\n[yellow]Administrative privileges required for full system scan.[/yellow]")
        
        if self.is_windows:
            console.print("[cyan]Please restart the application as Administrator.[/cyan]")
            console.print("Right-click the script and select 'Run as Administrator'")
            sys.exit(0)
        else:  # Linux
            console.print("[cyan]Requesting sudo privileges...[/cyan]")
            os.execvp('sudo', ['sudo', 'python3'] + sys.argv)
    
    def display_consent_screen(self):
        """Display permission request and get user consent"""
        console.clear()
        
        consent_text = """
[bold cyan]AI File Similarity & Deduplication Agent[/bold cyan]

[bold]This application needs your permission to:[/bold]

• Read files throughout your system
• Analyze file content for similarity detection
• Access folders (including system and hidden folders if authorized)
• Create reports and logs of duplicate files
• Move or delete duplicate files (with your confirmation)

[bold yellow]Privacy Guarantee:[/bold yellow]
✓ All processing happens locally on your machine
✓ No data is sent to external servers
✓ No internet connection required
✓ You control all file operations

[bold green]What happens next:[/bold green]
1. You choose which folders to scan
2. The AI analyzes files for duplicates
3. You review results and similarity percentages
4. You decide which files to keep or delete
        """
        
        console.print(Panel(consent_text, border_style="blue"))
        
        consent = Confirm.ask("\n[bold]Do you grant permission to proceed?[/bold]", default=False)
        
        if not consent:
            console.print("\n[red]Permission denied. Exiting.[/red]")
            sys.exit(0)
        
        return True
    
    def get_scan_scope(self):
        """Let user choose scan scope"""
        console.print("\n[bold cyan]Select Scan Scope:[/bold cyan]\n")
        console.print("1. Full System (All drives and folders - requires admin)")
        console.print("2. User Folders Only (Documents, Downloads, Desktop, Pictures)")
        console.print("3. Custom Folders (You select specific folders)")
        
        choice = Prompt.ask("\nEnter choice", choices=["1", "2", "3"], default="2")
        
        if choice == "1":
            if not self.check_admin_privileges():
                need_elevation = Confirm.ask(
                    "\n[yellow]Full system scan requires admin privileges. Request elevation?[/yellow]",
                    default=True
                )
                if need_elevation:
                    self.request_elevation()
                else:
                    console.print("[yellow]Falling back to User Folders mode.[/yellow]")
                    choice = "2"
            scope = "full_system"
            paths = self._get_full_system_paths()
        
        elif choice == "2":
            scope = "user_folders"
            paths = self._get_user_folder_paths()
        
        else:  # Custom
            scope = "custom"
            paths = self._get_custom_paths()
        
        return scope, paths
    
    def _get_full_system_paths(self):
        """Get all system root paths"""
        if self.is_windows:
            import string
            from ctypes import windll
            drives = []
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
            return drives
        else:  # Linux
            return ["/"]
    
    def _get_user_folder_paths(self):
        """Get common user folder paths"""
        home = Path.home()
        folders = []
        
        common_folders = ["Documents", "Downloads", "Desktop", "Pictures", 
                         "Videos", "Music"]
        
        for folder in common_folders:
            path = home / folder
            if path.exists():
                folders.append(str(path))
        
        return folders
    
    def _get_custom_paths(self):
        """Get custom paths from user"""
        console.print("\n[cyan]Enter folder paths to scan (one per line, empty line to finish):[/cyan]")
        paths = []
        
        while True:
            path = Prompt.ask("Folder path", default="")
            if not path:
                break
            
            path_obj = Path(path)
            if path_obj.exists() and path_obj.is_dir():
                paths.append(str(path_obj))
                console.print(f"[green]✓ Added: {path}[/green]")
            else:
                console.print(f"[red]✗ Invalid path: {path}[/red]")
        
        return paths
    
    def save_permission(self, scope, paths):
        """Save permission grant to config"""
        self.config['permissions']['granted'] = True
        self.config['permissions']['timestamp'] = datetime.now().isoformat()
        self.config['permissions']['scope'] = scope
        self.config['permissions']['custom_paths'] = paths
        self._save_config()
        
        console.print(f"\n[green]✓ Permission granted for {scope} scan[/green]")
        console.print(f"[dim]Scanning {len(paths)} location(s)[/dim]")
    
    def check_existing_permission(self):
        """Check if permission was previously granted"""
        return self.config['permissions']['granted']
    
    def revoke_permission(self):
        """Revoke previously granted permission"""
        self.config['permissions']['granted'] = False
        self.config['permissions']['timestamp'] = None
        self.config['permissions']['scope'] = "none"
        self.config['permissions']['custom_paths'] = []
        self._save_config()
        console.print("[yellow]Permission revoked. Re-authorization required on next run.[/yellow]")
    
    def authorize(self, force_reauth=False):
        """
        Main authorization flow
        Returns: (authorized: bool, scope: str, paths: list)
        """
        # Check existing permission
        if not force_reauth and self.check_existing_permission():
            scope = self.config['permissions']['scope']
            paths = self.config['permissions']['custom_paths']
            
            reuse = Confirm.ask(
                f"\n[cyan]Use previous authorization ({scope})?[/cyan]",
                default=True
            )
            
            if reuse:
                return True, scope, paths
        
        # Request new permission
        if not self.display_consent_screen():
            return False, None, []
        
        scope, paths = self.get_scan_scope()
        self.save_permission(scope, paths)
        
        return True, scope, paths
