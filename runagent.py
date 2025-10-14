#!/usr/bin/env python3
"""
AI File Similarity & Deduplication Agent
Main entry point
"""

from src.orchestrator import FileAgentOrchestrator
from rich.console import Console

console = Console()

def main():
    console.print("""
[bold cyan]
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║   AI File Similarity & Deduplication Agent            ║
║   Version 1.0                                         ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
[/bold cyan]
    """)
    
    # Create and run orchestrator
    agent = FileAgentOrchestrator()
    agent.run()
    
    console.print("\n[bold green]✓ Agent execution complete.[/bold green]\n")

if __name__ == "__main__":
    main()
