"""
Main Orchestrator
Coordinates all components and workflow
"""

import yaml
from rich.console import Console
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress

from src.permission_handler import PermissionHandler
from src.scanner import FileScanner
from src.reader import FileReader
from src.similarity import SimilarityEngine, cluster_duplicates
from src.database import DatabaseManager
from src.ui import ReviewUI
from src.file_ops import FileOperations
from src.logger import setup_logger
from src.utils import find_exact_duplicates_by_hash

console = Console()


class FileAgentOrchestrator:
    def __init__(self, config_path="config/settings.yaml"):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize logger
        self.logger = setup_logger(self.config)
        
        # Initialize components
        self.permission_handler = PermissionHandler(config_path)
        self.scanner = FileScanner(self.config)
        self.reader = FileReader(self.config)
        self.similarity_engine = SimilarityEngine(self.config)
        self.db = DatabaseManager()
        self.ui = ReviewUI(self.config)
        self.file_ops = FileOperations(self.config)
        
        self.logger.info("File Agent initialized")
    
    def run(self):
        """Main execution workflow"""
        try:
            # Step 1: Permission & Authorization
            console.print("[bold cyan]═══ Step 1: Authorization ═══[/bold cyan]")
            authorized, scope, paths = self.permission_handler.authorize()
            
            if not authorized:
                console.print("[red]Authorization failed. Exiting.[/red]")
                return
            
            self.logger.info(f"Authorized: {scope}, paths: {paths}")
            
            # Step 2: Scan File System
            console.print("\n[bold cyan]═══ Step 2: File System Scan ═══[/bold cyan]")
            files = self.scanner.scan_all(paths)
            
            if len(files) == 0:
                console.print("[yellow]No files found to process.[/yellow]")
                return
            
            self.logger.info(f"Scanned {len(files)} files")
            
            # Step 3: Fast Hash-Based Exact Duplicate Detection
            console.print("\n[bold cyan]═══ Step 3: Fast Hash Check (Exact Duplicates) ═══[/bold cyan]")
            exact_dupe_groups = find_exact_duplicates_by_hash(files)
            
            hash_duplicates = []
            if exact_dupe_groups:
                console.print(f"[green]✓ Found {len(exact_dupe_groups)} exact duplicate groups via hashing[/green]")
                
                # Convert hash groups to pair format
                for hash_val, file_group in exact_dupe_groups.items():
                    console.print(f"  [cyan]Hash group: {len(file_group)} identical files[/cyan]")
                    for i in range(len(file_group)):
                        for j in range(i + 1, len(file_group)):
                            hash_duplicates.append({
                                'file1': file_group[i],
                                'file2': file_group[j],
                                'similarity': 1.0,  # Exact match
                                'method': 'hash'
                            })
                
                self.logger.info(f"Found {len(hash_duplicates)} exact duplicate pairs via hashing")
            else:
                console.print("[yellow]No exact duplicates found via hashing[/yellow]")
            
            # Filter files for similarity computation
            hashed_paths = set()
            for file_group in exact_dupe_groups.values():
                for f in file_group:
                    hashed_paths.add(f['path'])
            
            files_for_similarity = [f for f in files if f['path'] not in hashed_paths]
            
            console.print(f"\n[cyan]Files remaining for similarity check: {len(files_for_similarity)}[/cyan]")
            
            # Step 4: Read File Contents (only for non-exact matches)
            near_duplicates = []
            if len(files_for_similarity) > 0:
                console.print("\n[bold cyan]═══ Step 4: Reading File Contents ═══[/bold cyan]")
                file_contents = self._read_all_files(files_for_similarity)
                
                # Step 5: Compute Similarities (with size bucketing)
                console.print("\n[bold cyan]═══ Step 5: Computing Similarities (TF-IDF/Embeddings) ═══[/bold cyan]")
                near_duplicates = self.similarity_engine.compute_similarity(file_contents)
                
                if near_duplicates:
                    console.print(f"[green]✓ Found {len(near_duplicates)} near-duplicate pairs[/green]")
                    self.logger.info(f"Found {len(near_duplicates)} near-duplicates")
            
            # Combine results
            all_duplicates = hash_duplicates + near_duplicates
            
            console.print(f"\n[bold green]✓ Total: {len(all_duplicates)} duplicate pairs found[/bold green]")
            console.print(f"  - Exact duplicates (hash): {len(hash_duplicates)}")
            console.print(f"  - Near duplicates (similarity): {len(near_duplicates)}")
            
            self.logger.info(f"Total duplicates: {len(all_duplicates)}")
            
            if len(all_duplicates) == 0:
                console.print("[yellow]No duplicates found.[/yellow]")
                return
            
            # Step 6: Cluster duplicates for better display
            console.print("\n[bold cyan]═══ Step 6: Clustering Duplicate Groups ═══[/bold cyan]")
            clusters = cluster_duplicates(all_duplicates)
            
            console.print(f"[green]✓ Grouped into {len(clusters)} duplicate clusters[/green]")
            for i, cluster in enumerate(clusters[:10], 1):  # Show first 10
                console.print(f"  Cluster {i}: {cluster['count']} files (avg similarity: {cluster['avg_similarity']:.2%})")
            
            if len(clusters) > 10:
                console.print(f"  ... and {len(clusters) - 10} more clusters")
            
            # Step 7: Cache Results (Batched for performance)
            if len(all_duplicates) > 0:
                console.print("\n[cyan]Caching results to database...[/cyan]")
                cursor = self.db.conn.cursor()
                
                # Prepare all file records first
                all_paths = set()
                for dup in all_duplicates:
                    all_paths.add(dup['file1']['path'])
                    all_paths.add(dup['file2']['path'])
                
                # Batch insert files
                for path in all_paths:
                    cursor.execute('INSERT OR IGNORE INTO files (path, size, modified) VALUES (?, ?, ?)',
                                (path, 0, 0))
                
                # Get all file IDs at once
                path_to_id = {}
                for path in all_paths:
                    cursor.execute('SELECT id FROM files WHERE path = ?', (path,))
                    result = cursor.fetchone()
                    if result:
                        path_to_id[path] = result[0]
                
                # Batch insert similarities
                similarity_records = [
                    (path_to_id[dup['file1']['path']], 
                     path_to_id[dup['file2']['path']], 
                     dup['similarity'])
                    for dup in all_duplicates
                    if dup['file1']['path'] in path_to_id and dup['file2']['path'] in path_to_id
                ]
                
                cursor.executemany('''
                    INSERT OR REPLACE INTO similarities (file1_id, file2_id, similarity)
                    VALUES (?, ?, ?)
                ''', similarity_records)
                
                self.db.conn.commit()
                console.print(f"[green]✓ Cached {len(similarity_records)} similarity records[/green]")
            
            # Step 8: User Review (now with clusters)
            console.print("\n[bold cyan]═══ Step 7: Review & Selection ═══[/bold cyan]")
            self.ui.display_duplicates(all_duplicates)
            
            files_to_delete = self.ui.review_and_select(all_duplicates)
            
            # Step 9: Confirm & Delete
            if files_to_delete and self.ui.confirm_deletion(files_to_delete):
                console.print("\n[bold cyan]═══ Step 8: File Operations ═══[/bold cyan]")
                success, failure, log = self.file_ops.bulk_delete(files_to_delete)
                
                console.print(f"\n[bold]Summary:[/bold]")
                console.print(f"  [green]✓ Success: {success}[/green]")
                console.print(f"  [red]✗ Failures: {failure}[/red]")
                
                self.logger.info(f"Deleted {success} files, {failure} failures")
            
            # Step 10: Generate Report (with clusters)
            self._generate_report(all_duplicates, files_to_delete, clusters)
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Operation cancelled by user.[/yellow]")
            self.logger.warning("Operation cancelled by user")
        
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            self.logger.error(f"Error in orchestrator: {e}", exc_info=True)
        
        finally:
            self.db.close()
    
    def _read_all_files(self, files):
        """Read contents of all files with progress"""
        file_contents = []
        max_workers = self.config['performance']['max_workers']
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Reading files...", total=len(files))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self.reader.read_file, f['path']): f 
                    for f in files
                }
                
                for future in as_completed(future_to_file):
                    file_meta = future_to_file[future]
                    try:
                        content = future.result()
                        file_contents.append((file_meta, content))
                    except Exception as e:
                        self.logger.error(f"Error reading {file_meta['path']}: {e}")
                    
                    progress.advance(task)
        
        return file_contents
    
    def _generate_report(self, duplicates, deleted_files, clusters=None):
        """Generate final report with clustering info"""
        import json
        from datetime import datetime
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_duplicates_found': len(duplicates),
            'total_clusters': len(clusters) if clusters else 0,
            'files_deleted': len(deleted_files) if deleted_files else 0,
            'clusters': clusters if clusters else [],
            'duplicates': duplicates,
            'deleted_files': self.file_ops.get_deletion_report()
        }
        
        report_path = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        console.print(f"\n[green]✓ Report saved: {report_path}[/green]")
