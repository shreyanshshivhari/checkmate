"""
File System Scanner
Recursively discovers files in specified paths
"""

import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

class FileScanner:
    def __init__(self, config):
        self.config = config
        self.skip_extensions = set(config['scanning']['skip_extensions'])
        self.skip_folders = set(config['scanning']['skip_folders'])
        self.max_size_bytes = config['scanning']['max_file_size_mb'] * 1024 * 1024
        self.include_hidden = config['scanning']['include_hidden']
        self.scanned_files = []
        
    def should_skip_folder(self, folder_name):
        """Check if folder should be skipped"""
        if not self.include_hidden and folder_name.startswith('.'):
            return True
        return folder_name in self.skip_folders
    
    def should_skip_file(self, file_path):
        """Check if file should be skipped"""
        try:
            path = Path(file_path)
            
            # Skip by extension
            if path.suffix.lower() in self.skip_extensions:
                return True
            
            # Skip hidden files
            if not self.include_hidden and path.name.startswith('.'):
                return True
            
            # Skip by size
            if path.stat().st_size > self.max_size_bytes:
                return True
            
            # Skip if not readable
            if not os.access(file_path, os.R_OK):
                return True
            
            return False
            
        except (OSError, PermissionError):
            return True
    
    def scan_directory(self, root_path):
        """Scan a single directory tree"""
        files = []
        
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                # Filter out skipped directories
                dirnames[:] = [d for d in dirnames if not self.should_skip_folder(d)]
                
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    
                    if not self.should_skip_file(file_path):
                        try:
                            stat = os.stat(file_path)
                            files.append({
                                'path': file_path,
                                'size': stat.st_size,
                                'modified': stat.st_mtime,
                                'name': filename
                            })
                        except (OSError, PermissionError) as e:
                            console.print(f"[dim red]Permission denied: {file_path}[/dim red]")
                            continue
        
        except PermissionError as e:
            console.print(f"[red]Cannot access: {root_path}[/red]")
        
        return files
    
    def scan_all(self, paths):
        """
        Scan all specified paths
        Returns: list of file metadata dictionaries
        """
        console.print(f"\n[bold cyan]Scanning {len(paths)} location(s)...[/bold cyan]\n")
        
        all_files = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]Discovering files...", total=len(paths))
            
            for path in paths:
                progress.update(task, description=f"[cyan]Scanning: {path}")
                files = self.scan_directory(path)
                all_files.extend(files)
                progress.advance(task)
        
        self.scanned_files = all_files
        
        console.print(f"\n[green]✓ Found {len(all_files)} files[/green]")
        
        return all_files
