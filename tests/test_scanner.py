"""
Tests for File Scanner
"""

import unittest
import os
import tempfile
from pathlib import Path
from src.scanner import FileScanner

class TestFileScanner(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.config = {
            'scanning': {
                'skip_extensions': ['.tmp'],
                'skip_folders': ['__pycache__'],
                'max_file_size_mb': 100,
                'include_hidden': False
            }
        }
        self.scanner = FileScanner(self.config)
        
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create test files
        Path(self.test_dir, "test1.txt").write_text("Test file 1")
        Path(self.test_dir, "test2.py").write_text("print('hello')")
        Path(self.test_dir, "test3.tmp").write_text("Temp file")
        Path(self.test_dir, ".hidden").write_text("Hidden file")
        
        # Create subdirectory
        subdir = Path(self.test_dir, "subdir")
        subdir.mkdir()
        Path(subdir, "nested.txt").write_text("Nested file")
    
    def tearDown(self):
        """Clean up test directory"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_should_skip_folder(self):
        """Test folder skip logic"""
        self.assertTrue(self.scanner.should_skip_folder("__pycache__"))
        self.assertTrue(self.scanner.should_skip_folder(".git"))
        self.assertFalse(self.scanner.should_skip_folder("normal_folder"))
    
    def test_should_skip_file(self):
        """Test file skip logic"""
        test_file = Path(self.test_dir, "test1.txt")
        tmp_file = Path(self.test_dir, "test3.tmp")
        
        self.assertFalse(self.scanner.should_skip_file(str(test_file)))
        self.assertTrue(self.scanner.should_skip_file(str(tmp_file)))
    
    def test_scan_directory(self):
        """Test directory scanning"""
        files = self.scanner.scan_directory(self.test_dir)
        
        # Should find .txt and .py files, not .tmp or hidden
        self.assertGreater(len(files), 0)
        
        # Check that files have required metadata
        for file_info in files:
            self.assertIn('path', file_info)
            self.assertIn('size', file_info)
            self.assertIn('modified', file_info)
            self.assertIn('name', file_info)
    
    def test_scan_all(self):
        """Test scanning multiple paths"""
        files = self.scanner.scan_all([self.test_dir])
        
        self.assertIsInstance(files, list)
        self.assertGreater(len(files), 0)

if __name__ == '__main__':
    unittest.main()
