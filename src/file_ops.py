"""
Safe File Operations
Handles file deletion and quarantine with safety checks
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from rich.console import Console

console = Console()

class FileOperations:
    def __init__(self, config):
        self.config = config
        self.quarantine = config['safety']['move_to_quarantine']
        self.quarantine_folder = Path(config['safety']['quarantine_folder'])
        self.deleted_files = []
        
        if self.quarantine:
            self.quarantine_folder.mkdir(parents=True, exist_ok=True)
    
    def safe_delete(self, file_path):
        """
        Safely delete or move file to quarantine
        Returns: (success: bool, message: str)
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return False, f"File not found: {file_path}"
            
            if self.quarantine:
                # Move to quarantine
                dest = self.quarantine_folder / path.name
                
                # Handle name conflicts
                if dest.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest = self.quarantine_folder / f"{path.stem}_{timestamp}{path.suffix}"
                
                shutil.move(str(path), str(dest))
                message = f"Moved to quarantine: {dest}"
            else:
                # Permanent deletion
                os.remove(file_path)
                message = f"Deleted: {file_path}"
            
            self.deleted_files.append({
                'original_path': file_path,
                'action': 'quarantined' if self.quarantine else 'deleted',
                'timestamp': datetime.now().isoformat()
            })
            
            return True, message
            
        except Exception as e:
            return False, f"Error deleting {file_path}: {str(e)}"
    
    def bulk_delete(self, file_paths):
        """
        Delete multiple files
        Returns: (success_count, failure_count, log)
        """
        success_count = 0
        failure_count = 0
        log = []
        
        console.print(f"\n[cyan]Processing {len(file_paths)} file(s)...[/cyan]\n")
        
        for file_path in file_paths:
            success, message = self.safe_delete(file_path)
            
            if success:
                console.print(f"[green]✓ {message}[/green]")
                success_count += 1
            else:
                console.print(f"[red]✗ {message}[/red]")
                failure_count += 1
            
            log.append(message)
        
        return success_count, failure_count, log
    
    def get_deletion_report(self):
        """Generate deletion report"""
        return self.deleted_files
