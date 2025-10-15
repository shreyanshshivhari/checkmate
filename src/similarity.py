"""
Similarity Computation Engine
Calculates similarity scores between file contents
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from rich.console import Console
from collections import defaultdict

console = Console()


def cluster_duplicates(duplicates):
    """
    Group files into clusters where all members are similar.
    Uses graph-based connected components algorithm.
    
    Returns: List of clusters, each cluster is a dict with:
        - files: list of file metadata
        - count: number of files in cluster
        - avg_similarity: average similarity score
    """
    # Build adjacency graph
    graph = defaultdict(set)
    file_map = {}  # path -> metadata
    
    for dup in duplicates:
        path1 = dup['file1']['path']
        path2 = dup['file2']['path']
        
        graph[path1].add(path2)
        graph[path2].add(path1)
        
        file_map[path1] = dup['file1']
        file_map[path2] = dup['file2']
    
    # Find connected components (clusters) using DFS
    visited = set()
    clusters = []
    
    def dfs(node, cluster):
        visited.add(node)
        cluster.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, cluster)
    
    for path in graph.keys():
        if path not in visited:
            cluster = []
            dfs(path, cluster)
            if len(cluster) > 1:  # Only keep actual duplicates
                # Calculate average similarity for cluster
                cluster_sims = [
                    d['similarity'] for d in duplicates 
                    if d['file1']['path'] in cluster and d['file2']['path'] in cluster
                ]
                avg_sim = sum(cluster_sims) / len(cluster_sims) if cluster_sims else 0
                
                # Add metadata to cluster
                cluster_with_meta = {
                    'files': [file_map[p] for p in cluster],
                    'count': len(cluster),
                    'avg_similarity': avg_sim
                }
                clusters.append(cluster_with_meta)
    
    # Sort by cluster size (largest first)
    clusters.sort(key=lambda c: c['count'], reverse=True)
    return clusters


class SimilarityEngine:
    def __init__(self, config):
        self.config = config
        self.method = config['similarity']['method']
        self.threshold = config['similarity']['threshold']
        
        if self.method == 'embeddings':
            model_name = config['similarity']['embedding_model']
            console.print(f"[cyan]Loading embedding model: {model_name}...[/cyan]")
            self.model = SentenceTransformer(model_name)
        else:
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2)
            )
    
    def preprocess_text(self, text):
        """Normalize and clean text"""
        if not text:
            return ""
        
        # Basic cleaning
        text = text.lower()
        text = ' '.join(text.split())  # Normalize whitespace
        
        return text
    
    def compute_tfidf_similarity(self, texts):
        """
        Compute similarity using TF-IDF + Cosine Similarity
        Returns: similarity matrix (NxN)
        """
        if len(texts) < 2:
            return np.array([[1.0]])
        
        try:
            # Transform texts to TF-IDF vectors
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Compute cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            return similarity_matrix
            
        except Exception as e:
            console.print(f"[red]Error in TF-IDF computation: {e}[/red]")
            return np.zeros((len(texts), len(texts)))
    
    def compute_embedding_similarity(self, texts):
        """
        Compute similarity using sentence embeddings
        Returns: similarity matrix (NxN)
        """
        if len(texts) < 2:
            return np.array([[1.0]])
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(texts, show_progress_bar=True)
            
            # Compute cosine similarity
            similarity_matrix = cosine_similarity(embeddings)
            
            return similarity_matrix
            
        except Exception as e:
            console.print(f"[red]Error in embedding computation: {e}[/red]")
            return np.zeros((len(texts), len(texts)))
    
    def _get_smart_size_bucket(self, file_size):
        """
        Smart size bucketing with logarithmic ranges.
        Groups files with similar sizes together (±10% tolerance).
        
        Returns: bucket_id (int)
        """
        if file_size == 0:
            return 0
        
        # Logarithmic bucketing
        if file_size < 1024:  # 0-1KB
            bucket = 0
        elif file_size < 10 * 1024:  # 1KB-10KB
            bucket = 1 + int(file_size / 1024)
        elif file_size < 100 * 1024:  # 10KB-100KB
            bucket = 10 + int(file_size / (10 * 1024))
        elif file_size < 1024 * 1024:  # 100KB-1MB
            bucket = 20 + int(file_size / (100 * 1024))
        elif file_size < 10 * 1024 * 1024:  # 1MB-10MB
            bucket = 30 + int(file_size / (1024 * 1024))
        elif file_size < 100 * 1024 * 1024:  # 10MB-100MB
            bucket = 40 + int(file_size / (10 * 1024 * 1024))
        else:  # 100MB+
            bucket = 50 + int(file_size / (100 * 1024 * 1024))
        
        return bucket
    
    def _format_size(self, bytes_size):
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
    
    def compute_similarity(self, file_contents):
        """
        OPTIMIZED similarity computation with SMART SIZE BUCKETING.
        
        Uses logarithmic size ranges instead of exact size matching:
        - Groups files with similar sizes together (±10% tolerance)
        - Dramatically reduces O(n²) comparisons
        - Catches near-duplicates even if file sizes differ slightly
        
        file_contents: list of (file_metadata, text_content) tuples
        Returns: list of duplicate pairs above threshold
        """
        console.print(f"\n[cyan]Computing similarities using {self.method.upper()} with SMART size bucketing...[/cyan]")
        
        # Create smart size buckets (logarithmic ranges)
        size_buckets = defaultdict(list)
        
        for meta, content in file_contents:
            file_size = meta.get('size', 0)
            
            # Get primary bucket
            primary_bucket = self._get_smart_size_bucket(file_size)
            size_buckets[primary_bucket].append((meta, content, file_size))
            
            # Also add to adjacent buckets if near boundary (±10% overlap)
            tolerance = int(file_size * 0.10)  # 10% tolerance
            
            if tolerance > 0:
                lower_bucket = self._get_smart_size_bucket(max(0, file_size - tolerance))
                upper_bucket = self._get_smart_size_bucket(file_size + tolerance)
                
                if lower_bucket != primary_bucket:
                    size_buckets[lower_bucket].append((meta, content, file_size))
                if upper_bucket != primary_bucket and upper_bucket != lower_bucket:
                    size_buckets[upper_bucket].append((meta, content, file_size))
        
        console.print(f"[cyan]Created {len(size_buckets)} smart size buckets (with 10% overlap)[/cyan]")
        
        all_duplicates = []
        processed_files = 0
        skipped_buckets = 0
        total_comparisons = 0
        
        # Process each bucket independently
        for bucket_id, bucket_contents in sorted(size_buckets.items()):
            bucket_size = len(bucket_contents)
            
            if bucket_size < 2:
                # Skip buckets with only 1 file
                skipped_buckets += 1
                processed_files += 1
                continue
            
            # Get size range for this bucket
            sizes = [size for _, _, size in bucket_contents]
            min_size = min(sizes)
            max_size = max(sizes)
            
            console.print(
                f"[cyan]Bucket {bucket_id}: {bucket_size} files "
                f"({self._format_size(min_size)} - {self._format_size(max_size)})[/cyan]"
            )
            
            # Extract metadata and texts
            metas = [m for m, _, _ in bucket_contents]
            texts = [self.preprocess_text(c) for _, c, _ in bucket_contents]
            
            # Compute similarity only within this bucket
            if self.method == 'embeddings':
                sim_matrix = self.compute_embedding_similarity(texts)
            else:  # tfidf
                sim_matrix = self.compute_tfidf_similarity(texts)
            
            # Extract pairs above threshold
            n = len(bucket_contents)
            bucket_pairs = 0
            bucket_comparisons = (n * (n - 1)) // 2  # Combinations
            total_comparisons += bucket_comparisons
            
            # Track seen pairs to avoid duplicates from overlapping buckets
            seen_pairs = set()
            
            for i in range(n):
                for j in range(i + 1, n):
                    similarity = sim_matrix[i][j]
                    
                    if similarity >= self.threshold:
                        path1 = metas[i]['path']
                        path2 = metas[j]['path']
                        
                        # Create canonical pair key (smaller path first)
                        pair_key = tuple(sorted([path1, path2]))
                        
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            all_duplicates.append({
                                'file1': metas[i],
                                'file2': metas[j],
                                'similarity': float(similarity),
                                'method': self.method,
                                'bucket_id': bucket_id
                            })
                            bucket_pairs += 1
            
            if bucket_pairs > 0:
                console.print(f"  [green]✓ Found {bucket_pairs} duplicate pairs ({bucket_comparisons} comparisons)[/green]")
            else:
                console.print(f"  [dim]No duplicates found ({bucket_comparisons} comparisons)[/dim]")
            
            processed_files += bucket_size
        
        # Remove duplicate pairs (from overlapping buckets)
        unique_duplicates = []
        seen_final = set()
        
        for dup in all_duplicates:
            pair_key = tuple(sorted([dup['file1']['path'], dup['file2']['path']]))
            if pair_key not in seen_final:
                seen_final.add(pair_key)
                unique_duplicates.append(dup)
        
        console.print(f"\n[bold cyan]Bucketing Performance:[/bold cyan]")
        console.print(f"  - Total files processed: {len(file_contents)}")
        console.print(f"  - Buckets created: {len(size_buckets)}")
        console.print(f"  - Buckets skipped (1 file): {skipped_buckets}")
        console.print(f"  - Buckets processed: {len(size_buckets) - skipped_buckets}")
        console.print(f"  - Total comparisons: {total_comparisons:,}")
        
        # Calculate naive comparison count
        naive_comparisons = (len(file_contents) * (len(file_contents) - 1)) // 2
        if naive_comparisons > 0:
            reduction = (1 - total_comparisons / naive_comparisons) * 100
            console.print(f"  - Naive comparisons would be: {naive_comparisons:,}")
            console.print(f"  - [bold green]Reduction: {reduction:.1f}%[/bold green]")
        
        console.print(f"  - Duplicate pairs before dedup: {len(all_duplicates)}")
        console.print(f"  - Unique duplicate pairs: {len(unique_duplicates)}")
        
        # Sort by similarity (highest first)
        unique_duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        
        return unique_duplicates
