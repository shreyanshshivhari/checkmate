"""
Logging Configuration
"""

import logging
from pathlib import Path

def setup_logger(config):
    """Configure logging"""
    log_file = config['logging']['file']
    log_level = config['logging']['level']
    
    # Create logs directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logger
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler() if config['logging']['console_output'] else logging.NullHandler()
        ]
    )
    
    return logging.getLogger('FileAgent')
