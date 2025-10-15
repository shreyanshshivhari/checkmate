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
        console.print("1. User Folders Only (Documents, Downloads, Desktop, Pictures)")
        console.print("2. Custom Folders (You select specific folders)")
        
        choice = Prompt.ask("\nEnter choice", choices=["1", "2"], default="1")
        
        if choice == "1":
            scope = "user_folders"
            paths = self._get_user_folder_paths()
        
        else:  # choice == "2" - Custom
            scope = "custom"
            paths = self._get_custom_paths()
        
        return scope, paths
    
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
        
        console.print(f"\n[cyan]Will scan the following user folders:[/cyan]")
        for folder_path in folders:
            console.print(f"  • {folder_path}")
        
        return folders
    
    def _get_custom_paths(self):
        """Get custom paths from user"""
        console.print("\n[cyan]Enter folder paths to scan (one per line, empty line to finish):[/cyan]")
        paths = []
        
        while True:
            path = Prompt.ask(f"Folder {len(paths) + 1} (or press Enter to finish)", default="")
            if not path:
                break
            
            path_obj = Path(path).expanduser()
            if path_obj.exists() and path_obj.is_dir():
                paths.append(str(path_obj))
                console.print(f"[green]✓ Added: {path}[/green]")
            else:
                console.print(f"[red]✗ Invalid path: {path}[/red]")
        
        if len(paths) == 0:
            console.print("[yellow]No folders selected. Defaulting to user folders.[/yellow]")
            return self._get_user_folder_paths()
        
        console.print(f"\n[cyan]Will scan {len(paths)} custom folder(s):[/cyan]")
        for folder_path in paths:
            console.print(f"  • {folder_path}")
        
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
        
        if not paths or len(paths) == 0:
            console.print("[red]No valid paths selected. Exiting.[/red]")
            return False, None, []
        
        self.save_permission(scope, paths)
        
        return True, scope, paths
