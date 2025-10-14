"""
User Interface for Review and Confirmation
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from pathlib import Path

console = Console()

class ReviewUI:
    def __init__(self, config):
        self.config = config
    
    def display_duplicates(self, duplicates):
        """Display duplicate pairs in a table"""
        if not duplicates:
            console.print("\n[green]✓ No duplicates found above threshold![/green]")
            return
        
        console.print(f"\n[bold cyan]Found {len(duplicates)} duplicate pair(s)[/bold cyan]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("File 1", style="cyan")
        table.add_column("File 2", style="yellow")
        table.add_column("Similarity", justify="right", style="green")
        table.add_column("Size 1", justify="right")
        table.add_column("Size 2", justify="right")
        
        for idx, dup in enumerate(duplicates, 1):
            file1 = dup['file1']
            file2 = dup['file2']
            similarity = f"{dup['similarity']*100:.1f}%"
            size1 = self.format_size(file1['size'])
            size2 = self.format_size(file2['size'])
            
            table.add_row(
                str(idx),
                str(Path(file1['path']).name),
                str(Path(file2['path']).name),
                similarity,
                size1,
                size2
            )
        
        console.print(table)
    
    def format_size(self, bytes):
        """Format file size in human-readable form"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"
    
    def review_and_select(self, duplicates):
        """
        Interactive review of duplicates
        Returns: list of files to delete
        """
        if not duplicates:
            return []
        
        to_delete = []
        
        console.print("\n[bold yellow]Review each duplicate pair:[/bold yellow]\n")
        
        for idx, dup in enumerate(duplicates, 1):
            file1 = dup['file1']
            file2 = dup['file2']
            similarity = dup['similarity']
            
            # Display comparison
            panel_content = f"""
[bold]Pair {idx} of {len(duplicates)}[/bold]
Similarity: [green]{similarity*100:.1f}%[/green]

[cyan]File 1:[/cyan] {file1['path']}
  Size: {self.format_size(file1['size'])}
  Modified: {self.format_timestamp(file1['modified'])}

[yellow]File 2:[/yellow] {file2['path']}
  Size: {self.format_size(file2['size'])}
  Modified: {self.format_timestamp(file2['modified'])}
            """
            
            console.print(Panel(panel_content, border_style="blue"))
            
            # Ask user what to do
            console.print("\n[bold]What would you like to do?[/bold]")
            console.print("1. Delete File 1 (keep File 2)")
            console.print("2. Delete File 2 (keep File 1)")
            console.print("3. Delete both")
            console.print("4. Keep both (skip)")
            
            choice = Prompt.ask("Your choice", choices=["1", "2", "3", "4"], default="4")
            
            if choice == "1":
                to_delete.append(file1['path'])
            elif choice == "2":
                to_delete.append(file2['path'])
            elif choice == "3":
                to_delete.append(file1['path'])
                to_delete.append(file2['path'])
            
            console.print()
        
        return to_delete
    
    def format_timestamp(self, timestamp):
        """Format Unix timestamp to readable date"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    def confirm_deletion(self, files_to_delete):
        """Final confirmation before deletion"""
        if not files_to_delete:
            console.print("\n[yellow]No files selected for deletion.[/yellow]")
            return False
        
        console.print(f"\n[bold red]You are about to delete {len(files_to_delete)} file(s):[/bold red]\n")
        
        for file_path in files_to_delete:
            console.print(f"  • {file_path}")
        
        return Confirm.ask("\n[bold]Proceed with deletion?[/bold]", default=False)
