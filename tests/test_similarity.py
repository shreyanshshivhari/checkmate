"""
Tests for Similarity Engine
"""

import unittest
from src.similarity import SimilarityEngine

class TestSimilarityEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'similarity': {
                'method': 'tfidf',
                'threshold': 0.8,
                'embedding_model': 'all-MiniLM-L6-v2'
            }
        }
        self.engine = SimilarityEngine(self.config)
    
    def test_preprocess_text(self):
        """Test text preprocessing"""
        text = "  Hello   World  \n  Test  "
        processed = self.engine.preprocess_text(text)
        
        self.assertEqual(processed, "hello world test")
    
    def test_compute_tfidf_similarity_identical(self):
        """Test similarity of identical texts"""
        texts = ["This is a test document", "This is a test document"]
        sim_matrix = self.engine.compute_tfidf_similarity(texts)
        
        # Similarity should be 1.0 for identical texts
        self.assertAlmostEqual(sim_matrix[0][1], 1.0, places=2)
    
    def test_compute_tfidf_similarity_different(self):
        """Test similarity of different texts"""
        texts = ["Python programming language", "Java coffee drink"]
        sim_matrix = self.engine.compute_tfidf_similarity(texts)
        
        # Similarity should be low for different texts
        self.assertLess(sim_matrix[0][1], 0.5)
    
    def test_compute_tfidf_similarity_similar(self):
        """Test similarity of similar texts"""
        texts = [
            "The quick brown fox jumps over the lazy dog",
            "The quick brown fox jumps over a lazy dog"
        ]
        sim_matrix = self.engine.compute_tfidf_similarity(texts)
        
        # Similarity should be high for similar texts
        self.assertGreater(sim_matrix[0][1], 0.7)
    
    def test_compute_similarity(self):
        """Test main similarity computation"""
        file_contents = [
            ({'path': 'file1.txt', 'size': 100}, "This is document one"),
            ({'path': 'file2.txt', 'size': 100}, "This is document one"),
            ({'path': 'file3.txt', 'size': 100}, "Completely different content")
        ]
        
        duplicates = self.engine.compute_similarity(file_contents)
        
        # Should find at least one duplicate pair (file1 and file2)
        self.assertGreater(len(duplicates), 0)
        
        # First duplicate should have high similarity
        self.assertGreater(duplicates[0]['similarity'], 0.8)

if __name__ == '__main__':
    unittest.main()
