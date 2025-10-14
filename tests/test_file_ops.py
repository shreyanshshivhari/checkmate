"""
Tests for File Operations
"""

import unittest
import os
import tempfile
from pathlib import Path
from src.file_ops import FileOperations

class TestFileOperations(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.quarantine_dir = Path(self.test_dir, "quarantine")
        
        self.config = {
            'safety': {
                'move_to_quarantine': True,
                'quarantine_folder': str(self.quarantine_dir)
            }
        }
        self.file_ops = FileOperations(self.config)
        
        # Create test file
        self.test_file = Path(self.test_dir, "test.txt")
        self.test_file.write_text("Test content")
    
    def tearDown(self):
        """Clean up test directory"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_safe_delete_with_quarantine(self):
        """Test moving file to quarantine"""
        success, message = self.file_ops.safe_delete(str(self.test_file))
        
        self.assertTrue(success)
        self.assertFalse(self.test_file.exists())
        self.assertTrue((self.quarantine_dir / "test.txt").exists())
    
    def test_safe_delete_nonexistent(self):
        """Test deleting non-existent file"""
        fake_file = Path(self.test_dir, "nonexistent.txt")
        success, message = self.file_ops.safe_delete(str(fake_file))
        
        self.assertFalse(success)
        self.assertIn("not found", message)
    
    def test_bulk_delete(self):
        """Test bulk deletion"""
        # Create multiple test files
        files = []
        for i in range(3):
            file_path = Path(self.test_dir, f"file{i}.txt")
            file_path.write_text(f"Content {i}")
            files.append(str(file_path))
        
        success_count, failure_count, log = self.file_ops.bulk_delete(files)
        
        self.assertEqual(success_count, 3)
        self.assertEqual(failure_count, 0)
        self.assertEqual(len(log), 3)
    
    def test_get_deletion_report(self):
        """Test deletion report generation"""
        self.file_ops.safe_delete(str(self.test_file))
        
        report = self.file_ops.get_deletion_report()
        
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]['original_path'], str(self.test_file))
        self.assertIn('timestamp', report[0])

if __name__ == '__main__':
    unittest.main()
