"""
Similarity Computation Engine
Calculates similarity scores between file contents
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from rich.console import Console

console = Console()

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
    
    def compute_similarity(self, file_contents):
        """
        Main similarity computation
        file_contents: list of (file_metadata, text_content) tuples
        Returns: list of (file1, file2, similarity_score) tuples
        """
        console.print(f"\n[cyan]Computing similarities using {self.method.upper()}...[/cyan]")
        
        # Preprocess all texts
        texts = [self.preprocess_text(content) for _, content in file_contents]
        
        # Compute similarity matrix
        if self.method == 'embeddings':
            sim_matrix = self.compute_embedding_similarity(texts)
        else:  # tfidf
            sim_matrix = self.compute_tfidf_similarity(texts)
        
        # Extract duplicate pairs above threshold
        duplicates = []
        n = len(file_contents)
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = sim_matrix[i][j]
                
                if similarity >= self.threshold:
                    file1, _ = file_contents[i]
                    file2, _ = file_contents[j]
                    
                    duplicates.append({
                        'file1': file1,
                        'file2': file2,
                        'similarity': float(similarity)
                    })
        
        # Sort by similarity (highest first)
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        
        return duplicates
