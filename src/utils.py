"""
Utility Functions
Helper functions for file operations and hashing
"""

import hashlib
from pathlib import Path
from collections import defaultdict


def fast_hash_file(path, chunk_size=8192):
    """
    Fast SHA-256 hash of file contents
    Args:
        path: File path to hash
        chunk_size: Read chunk size for memory efficiency
    Returns:
        Hex string of hash or None on error
    """
    hasher = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return None


def find_exact_duplicates_by_hash(files):
    """
    Fast exact duplicate detection using file hashing.
    Groups files by their SHA-256 hash.
    
    Args:
        files: List of file metadata dicts with 'path' key
    
    Returns:
        dict of {hash: [file_metadata_list]} for groups with 2+ files
    """
    hash_to_files = defaultdict(list)
    
    for file_meta in files:
        file_hash = fast_hash_file(file_meta['path'])
        if file_hash:
            # Add hash to metadata for later filtering
            file_meta['content_hash'] = file_hash
            hash_to_files[file_hash].append(file_meta)
    
    # Return only groups with duplicates (2+ files with same hash)
    return {h: files for h, files in hash_to_files.items() if len(files) > 1}


def get_size_bucket(file_size):
    """
    Assign file to a size bucket based on logarithmic ranges.
    This allows fuzzy matching of files with similar (but not identical) sizes.
    
    Buckets:
    - 0-1KB: bucket 0 (0-1024)
    - 1KB-10KB: buckets 1-9 (1024-10240, subdivided)
    - 10KB-100KB: buckets 10-19 (10240-102400, subdivided)
    - 100KB-1MB: buckets 20-29
    - 1MB-10MB: buckets 30-39
    - 10MB+: buckets 40+
    
    Args:
        file_size: File size in bytes
    
    Returns:
        Bucket ID (int)
    """
    if file_size == 0:
        return 0
    
    # Logarithmic bucketing with ±10% tolerance
    import math
    
    # Calculate bucket based on order of magnitude
    if file_size < 1024:  # 0-1KB
        return 0
    elif file_size < 10 * 1024:  # 1KB-10KB
        return 1 + int(file_size / 1024)  # buckets 1-10
    elif file_size < 100 * 1024:  # 10KB-100KB
        return 10 + int(file_size / (10 * 1024))  # buckets 10-20
    elif file_size < 1024 * 1024:  # 100KB-1MB
        return 20 + int(file_size / (100 * 1024))  # buckets 20-30
    elif file_size < 10 * 1024 * 1024:  # 1MB-10MB
        return 30 + int(file_size / (1024 * 1024))  # buckets 30-40
    elif file_size < 100 * 1024 * 1024:  # 10MB-100MB
        return 40 + int(file_size / (10 * 1024 * 1024))  # buckets 40-50
    else:  # 100MB+
        return 50 + int(file_size / (100 * 1024 * 1024))  # buckets 50+


def create_size_buckets_with_overlap(files, tolerance_percent=10):
    """
    Create size buckets with OVERLAP to catch near-duplicates.
    Files are placed in multiple adjacent buckets if they're near boundaries.
    
    Args:
        files: List of file metadata dicts with 'size' key
        tolerance_percent: Percentage tolerance for size matching (default 10%)
    
    Returns:
        dict of {bucket_id: [file_metadata_list]}
    """
    buckets = defaultdict(list)
    
    for file_meta in files:
        size = file_meta.get('size', 0)
        
        # Primary bucket
        primary_bucket = get_size_bucket(size)
        buckets[primary_bucket].append(file_meta)
        
        # Add to adjacent buckets if near boundary (±tolerance)
        tolerance = size * (tolerance_percent / 100)
        
        lower_size = max(0, size - tolerance)
        upper_size = size + tolerance
        
        lower_bucket = get_size_bucket(lower_size)
        upper_bucket = get_size_bucket(upper_size)
        
        # Add to adjacent buckets if different from primary
        if lower_bucket != primary_bucket:
            buckets[lower_bucket].append(file_meta)
        if upper_bucket != primary_bucket and upper_bucket != lower_bucket:
            buckets[upper_bucket].append(file_meta)
    
    return buckets


def format_file_size(bytes_size):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"
