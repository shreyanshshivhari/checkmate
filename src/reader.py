"""
File Content Reader
Extracts text content from various file types
"""

import os
from pathlib import Path
import PyPDF2
import docx

class FileReader:
    def __init__(self, config):
        self.config = config
        self.chunk_size = config['performance']['chunk_size_kb'] * 1024
    
    def read_text_file(self, file_path):
        """Read plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return ""
    
    def read_pdf(self, file_path):
        """Extract text from PDF"""
        try:
            text = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return ' '.join(text)
        except Exception as e:
            return ""
    
    def read_docx(self, file_path):
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            return ' '.join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            return ""
    
    def read_file(self, file_path):
        """
        Read file content based on extension
        Returns: extracted text content
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # PDF files
        if extension == '.pdf':
            return self.read_pdf(file_path)
        
        # Word documents
        elif extension in ['.docx', '.doc']:
            return self.read_docx(file_path)
        
        # Text files
        elif extension in ['.txt', '.md', '.py', '.java', '.cpp', '.js', 
                          '.html', '.css', '.json', '.xml', '.csv', '.log']:
            return self.read_text_file(file_path)
        
        # Binary files - read as bytes sample
        else:
            try:
                with open(file_path, 'rb') as f:
                    # Read first chunk only for binary comparison
                    return f.read(self.chunk_size).decode('utf-8', errors='ignore')
            except:
                return ""
