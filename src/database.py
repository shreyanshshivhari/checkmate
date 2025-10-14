"""
SQLite Database Manager
Caches similarity results and file metadata
"""

import sqlite3
import json
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="data/similarity_cache.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                size INTEGER,
                modified REAL,
                content_hash TEXT,
                last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Similarities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS similarities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file1_id INTEGER,
                file2_id INTEGER,
                similarity REAL,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file1_id) REFERENCES files(id),
                FOREIGN KEY (file2_id) REFERENCES files(id),
                UNIQUE(file1_id, file2_id)
            )
        ''')
        
        self.conn.commit()
    
    def store_file(self, file_metadata):
        """Store or update file metadata"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO files (path, size, modified)
            VALUES (?, ?, ?)
        ''', (file_metadata['path'], file_metadata['size'], file_metadata['modified']))
        self.conn.commit()
        return cursor.lastrowid
    
    def store_similarity(self, file1_path, file2_path, similarity):
        """Store similarity score"""
        try:
            cursor = self.conn.cursor()
            
            # First, ensure both files exist in database
            cursor.execute('SELECT id FROM files WHERE path = ?', (file1_path,))
            result1 = cursor.fetchone()
            if result1:
                file1_id = result1[0]
            else:
                # File not in database, store it first
                cursor.execute('INSERT INTO files (path, size, modified) VALUES (?, ?, ?)',
                              (file1_path, 0, 0))
                file1_id = cursor.lastrowid
            
            cursor.execute('SELECT id FROM files WHERE path = ?', (file2_path,))
            result2 = cursor.fetchone()
            if result2:
                file2_id = result2[0]
            else:
                # File not in database, store it first
                cursor.execute('INSERT INTO files (path, size, modified) VALUES (?, ?, ?)',
                              (file2_path, 0, 0))
                file2_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT OR REPLACE INTO similarities (file1_id, file2_id, similarity)
                VALUES (?, ?, ?)
            ''', (file1_id, file2_id, similarity))
            
            self.conn.commit()
        except Exception as e:
            # Silently skip database errors
            pass
    
    def get_cached_similarity(self, file1_path, file2_path):
        """Retrieve cached similarity if exists"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT s.similarity FROM similarities s
            JOIN files f1 ON s.file1_id = f1.id
            JOIN files f2 ON s.file2_id = f2.id
            WHERE (f1.path = ? AND f2.path = ?)
               OR (f1.path = ? AND f2.path = ?)
        ''', (file1_path, file2_path, file2_path, file1_path))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
