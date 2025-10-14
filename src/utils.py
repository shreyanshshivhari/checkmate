"""
Utility Functions
"""

from pathlib import Path

def normalize_path(path_str):
    """Normalize file path for cross-platform compatibility"""
    return str(Path(path_str).resolve())

def get_file_extension(file_path):
    """Get file extension in lowercase"""
    return Path(file_path).suffix.lower()

def format_bytes(bytes_count):
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.2f} PB"
